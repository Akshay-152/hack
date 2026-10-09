"""Registration endpoints (PLAN API section 9) with server-side rules:
duplicate prevention, capacity, and registration deadlines."""
from __future__ import annotations

import json
import pathlib  # noqa: F401  (placeholder to keep module importable standalone)

from flask import Blueprint, current_app, g, jsonify

from auth_service import auth_required

bp = Blueprint("registrations", __name__)


def _event_registrable(event: dict | None) -> tuple[dict | None, str | None]:
    """Validate that registration can proceed; returns (event, error)."""
    if not event or event.get("status") != "published":
        return None, "event not found"

    from storage import utcnow
    now = utcnow()

    from services.recommender import event_is_past
    if event_is_past(event, now):
        return None, "event already ended"

    deadline = event.get("registrationDeadline")
    if deadline:
        try:
            from datetime import datetime
            if datetime.fromisoformat(deadline) < now:
                return None, "registration deadline passed"
        except ValueError:
            pass

    if event.get("registeredCount", 0) >= event.get("capacity", 0):
        return None, "event is full"
    return event, None


@bp.post("/api/events/<event_id>/register")
@auth_required()
def register(event_id):
    existing = current_app.store.get_registration(g.uid, event_id)
    if existing:
        return jsonify(error="already registered for this event"), 409

    event = current_app.store.get_event(event_id)
    event, err = _event_registrable(event)
    if err:
        status = 404 if err == "event not found" else 400
        return jsonify(error=err), status

    reg = current_app.store.add_registration(g.uid, event_id)
    return jsonify(registration=reg), 201


@bp.post("/api/events/<event_id>/cancel-registration")
@auth_required()
def cancel(event_id):
    reg = current_app.store.cancel_registration(g.uid, event_id)
    if not reg:
        return jsonify(error="no registration found"), 404
    return jsonify(registration=reg)


@bp.get("/api/my-registrations")
@auth_required()
def my_registrations():
    regs = current_app.store.list_registrations_for_user(g.uid)
    events = []
    for r in regs:
        event = current_app.store.get_event(r["eventId"])
        if event:
            events.append({"registration": r, "event": event})
    return jsonify(registrations=events)
