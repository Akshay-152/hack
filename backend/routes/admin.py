"""Admin-only event management endpoints (PLAN API section 9)."""
from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify, request

from auth_service import auth_required

bp = Blueprint("admin", __name__)

REQUIRED_FIELDS = ("title", "date", "capacity", "category")


def _validate_event_payload(data: dict, *, partial: bool = False) -> str | None:
    """Return an error message, or None when payload is acceptable."""
    for f in REQUIRED_FIELDS:
        if not partial and not data.get(f):
            return f"missing required field: {f}"

    if "capacity" in data:
        cap = data["capacity"]
        if not isinstance(cap, int) or cap <= 0:
            return "capacity must be a positive integer"

    for date_field in ("date", "registrationDeadline"):
        if date_field in data and data[date_field]:
            try:
                from datetime import datetime
                datetime.fromisoformat(str(data[date_field]))
            except ValueError:
                return f"{date_field} must be ISO format (YYYY-MM-DD)"

    if "status" in data and data["status"] not in ("draft", "published", "cancelled"):
        return "status must be draft, published, or cancelled"
    if "tags" in data and not isinstance(data.get("tags"), list):
        return "tags must be a list"
    return None


def _clean(data: dict) -> dict:
    allowed = {"title", "description", "category", "tags", "date", "startTime",
               "endTime", "venue", "organizer", "registrationDeadline",
               "capacity", "status", "registrationUrl", "targetAudience"}
    return {k: v for k, v in data.items() if k in allowed}


@bp.get("/api/admin/events")
@auth_required(require_admin=True)
def admin_list_events():
    return jsonify(events=current_app.store.list_events())


@bp.post("/api/admin/events")
@auth_required(require_admin=True)
def create_event():
    data = request.get_json(silent=True) or {}
    err = _validate_event_payload(data)
    if err:
        return jsonify(error=err), 400
    event = current_app.store.add_event({
        "status": data.get("status", "draft"),
        **_clean(data),
        "createdBy": g.uid,
    })
    return jsonify(event=event), 201


@bp.put("/api/admin/events/<event_id>")
@auth_required(require_admin=True)
def update_event(event_id):
    data = request.get_json(silent=True) or {}
    err = _validate_event_payload(data, partial=True)
    if err:
        return jsonify(error=err), 400
    event = current_app.store.update_event(event_id, _clean(data))
    if not event:
        return jsonify(error="event not found"), 404
    return jsonify(event=event)


@bp.post("/api/admin/events/<event_id>/cancel")
@auth_required(require_admin=True)
def cancel_event(event_id):
    event = current_app.store.update_event(event_id, {"status": "cancelled"})
    if not event:
        return jsonify(error="event not found"), 404
    return jsonify(event=event)
