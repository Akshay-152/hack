"""Data storage layer for the Campus Event Recommendation Bot.

The storage interface mirrors the Firestore collections described in
PLAN.md section 7: users, events, registrations.

* MemoryStore  - a dictionary-backed store used for local development
  and tests (no external services required).
* FirestoreStore - thin wrapper around firebase-admin Firestore, used
  when DB_BACKEND=firestore. Import is deferred so firebase-admin is
  only needed when actually enabled.

All uniqueness/concurrency-sensitive rules (duplicate registration,
capacity) are enforced in the application layer so behaviour is
identical across backends.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naive UTC 'now' — matches the naive ISO dates stored on events."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class MemoryStore:
    """Simple in-memory implementation with Firestore-like document dicts."""

    def __init__(self) -> None:
        self.users: dict[str, dict] = {}
        self.events: dict[str, dict] = {}
        self.registrations: dict[str, dict] = {}

    # -- generic helpers -------------------------------------------------
    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex[:16]

    def add_user(self, uid: str, data: dict) -> dict:
        user = {"uid": uid, **data, "createdAt": utcnow().isoformat()}
        self.users[uid] = user
        return dict(user)

    def get_user(self, uid: str) -> dict | None:
        user = self.users.get(uid)
        return dict(user) if user else None

    def update_user(self, uid: str, data: dict) -> dict | None:
        if uid not in self.users:
            return None
        self.users[uid].update(data)
        return dict(self.users[uid])

    # -- events ----------------------------------------------------------
    def add_event(self, data: dict) -> dict:
        event_id = self.new_id()
        event = {
            "eventId": event_id,
            **data,
            "createdAt": utcnow().isoformat(),
            "registeredCount": 0,
        }
        self.events[event_id] = event
        return dict(event)

    def get_event(self, event_id: str) -> dict | None:
        event = self.events.get(event_id)
        return dict(event) if event else None

    def update_event(self, event_id: str, data: dict) -> dict | None:
        if event_id not in self.events:
            return None
        self.events[event_id].update(data)
        return dict(self.events[event_id])

    def list_events(self) -> list[dict]:
        if not self.events:
            return []
        return [dict(e) for e in self.events.values()]

    # -- registrations ---------------------------------------------------
    def add_registration(self, uid: str, event_id: str) -> dict:
        reg_id = f"{event_id}__{uid}"  # uniqueness by (eventId, uid)
        reg = {
            "registrationId": reg_id,
            "eventId": event_id,
            "uid": uid,
            "registeredAt": utcnow().isoformat(),
            "status": "confirmed",
        }
        self.registrations[reg_id] = reg
        event = self.events[event_id]
        event["registeredCount"] = event.get("registeredCount", 0) + 1
        return dict(reg)

    def get_registration(self, uid: str, event_id: str) -> dict | None:
        reg = self.registrations.get(f"{event_id}__{uid}")
        return dict(reg) if reg else None

    def cancel_registration(self, uid: str, event_id: str) -> dict | None:
        reg = self.registrations.get(f"{event_id}__{uid}")
        if not reg:
            return None
        reg["status"] = "cancelled"
        event = self.events[event_id]
        event["registeredCount"] = max(0, event.get("registeredCount", 1) - 1)
        self.registrations.pop(f"{event_id}__{uid}")
        return dict(reg)

    def list_registrations_for_user(self, uid: str) -> list[dict]:
        return [dict(r) for r in self.registrations.values() if r["uid"] == uid]


class FirestoreStore:
    """Firestore-backed store using firebase-admin.

    Requires FIREBASE_CREDENTIALS (path to the service-account JSON)
    and FIREBASE_PROJECT_ID from the environment.
    """

    def __init__(self, credentials_path: str, project_id: str) -> None:
        import firebase_admin
        from firebase_admin import credentials, firestore

        cred = credentials.Certificate(credentials_path)
        firebase_admin.initialize_app(cred, {"projectId": project_id})
        self.db = firestore.client()

    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex[:16]

    def add_user(self, uid: str, data: dict) -> dict:
        user = {"uid": uid, **data, "createdAt": utcnow().isoformat()}
        self.db.collection("users").document(uid).set(user)
        return user

    def get_user(self, uid: str) -> dict | None:
        doc = self.db.collection("users").document(uid).get()
        return doc.to_dict() if doc.exists else None

    def update_user(self, uid: str, data: dict) -> dict | None:
        ref = self.db.collection("users").document(uid)
        ref.set(data, merge=True)
        return self.get_user(uid)

    def add_event(self, data: dict) -> dict:
        event_id = self.new_id()
        event = {"eventId": event_id, **data, "createdAt": utcnow().isoformat(),
                 "registeredCount": 0}
        self.db.collection("events").document(event_id).set(event)
        return event

    def get_event(self, event_id: str) -> dict | None:
        doc = self.db.collection("events").document(event_id).get()
        return doc.to_dict() if doc.exists else None

    def update_event(self, event_id: str, data: dict) -> dict | None:
        ref = self.db.collection("events").document(event_id)
        ref.set(data, merge=True)
        return self.get_event(event_id)

    def list_events(self) -> list[dict]:
        return [doc.to_dict() | {"eventId": doc.id}
                for doc in self.db.collection("events").stream()]

    def add_registration(self, uid: str, event_id: str) -> dict:
        """Transactionally create a registration and increment count."""
        from firebase_admin import firestore as fs

        reg_id = f"{event_id}__{uid}"
        reg_ref = self.db.collection("registrations").document(reg_id)
        event_ref = self.db.collection("events").document(event_id)

        @fs.transactional
        def _create(tx):
            if reg_ref.get(transaction=tx).exists:
                raise ValueError("duplicate registration")
            event_doc = event_ref.get(transaction=tx)
            if not event_doc.exists:
                raise ValueError("event not found")
            event = event_doc.to_dict()
            if event.get("registeredCount", 0) >= event.get("capacity", 0):
                raise ValueError("event is full")
            tx.set(reg_ref, {
                "eventId": event_id, "uid": uid,
                "registeredAt": utcnow().isoformat(), "status": "confirmed",
            })
            tx.update(event_ref, {
                "registeredCount": fs.Increment(1),
            })

        _create(self.db.transaction())
        return {"registrationId": reg_id, "eventId": event_id, "uid": uid,
                "status": "confirmed"}

    def get_registration(self, uid: str, event_id: str) -> dict | None:
        doc = self.db.collection("registrations").document(f"{event_id}__{uid}").get()
        return doc.to_dict() if doc.exists else None

    def cancel_registration(self, uid: str, event_id: str) -> dict | None:
        from firebase_admin import firestore as fs

        reg_ref = self.db.collection("registrations").document(f"{event_id}__{uid}")
        event_ref = self.db.collection("events").document(event_id)
        if not reg_ref.get().exists:
            return None
        reg = reg_ref.get().to_dict()
        reg_ref.set({"status": "cancelled"}, merge=True)
        event_ref.update({"registeredCount": fs.Increment(-1)})
        return reg | {"status": "cancelled"}

    def list_registrations_for_user(self, uid: str) -> list[dict]:
        docs = (self.db.collection("registrations")
                .where("uid", "==", uid).stream())
        return [d.to_dict() | {"registrationId": d.id} for d in docs]


def get_store(config) -> MemoryStore | FirestoreStore:
    """Build the store configured in config.DB_BACKEND."""
    if config["DB_BACKEND"] == "firestore":
        if not config["FIREBASE_CREDENTIALS"] or not config["FIREBASE_PROJECT_ID"]:
            raise RuntimeError(
                "DB_BACKEND=firestore requires FIREBASE_CREDENTIALS and "
                "FIREBASE_PROJECT_ID in .env"
            )
        return FirestoreStore(config["FIREBASE_CREDENTIALS"], config["FIREBASE_PROJECT_ID"])
    return MemoryStore()
