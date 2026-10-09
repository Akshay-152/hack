"""Public event endpoints (PLAN API section 9)."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

bp = Blueprint("events", __name__)


def _filter_events(events: list[dict], args) -> list[dict]:
    """Apply category, date, department, and keyword filters."""
    category = (args.get("category") or "").strip().lower()
    date = (args.get("date") or "").strip()
    department = (args.get("department") or "").strip().lower()
    q = (args.get("q") or "").strip().lower()

    out = []
    for e in events:
        if category and e.get("category", "").lower() != category:
            continue
        if date and e.get("date") != date:
            continue
        if department:
            audience = [a.lower() for a in e.get("targetAudience", [])]
            if department not in audience:
                continue
        if q and q not in (e.get("title", "") + e.get("description", "")).lower():
            continue
        out.append(e)
    return out


def _serialize(e: dict, now_iso: str) -> dict:
    data = dict(e)
    reg_open = (
        e.get("registeredCount", 0) < e.get("capacity", 0)
        and (not e.get("registrationDeadline") or e["registrationDeadline"] > now_iso)
    )
    data["registrationOpen"] = reg_open
    return data


@bp.get("/api/events")
def list_events():
    from storage import utcnow
    now = utcnow().isoformat()
    published = [e for e in current_app.store.list_events()
                 if e.get("status") == "published" and e.get("date", "") >= now[:10]]
    return jsonify(events=_filter_events(published, request.args))


@bp.get("/api/events/<event_id>")
def get_event(event_id):
    from storage import utcnow
    event = current_app.store.get_event(event_id)
    if not event or event.get("status") != "published":
        return jsonify(error="event not found"), 404
    return jsonify(event=_serialize(event, utcnow().isoformat()))
