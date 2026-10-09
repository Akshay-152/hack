"""Public event endpoints (spec section 5 dashboard data)."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from auth_service import load_session_user
import db
from helpers import event_to_dict, registration_open

bp = Blueprint("events", __name__)


@bp.get("/api/events")
def list_events():
    """Published, non-past events; filters: category, q, date."""
    rows = db.query(
        "SELECT * FROM events WHERE status='published' "
        "ORDER BY event_date, start_time")
    now_date = db.now_iso()[:10]
    out = []
    for row in rows:
        e = event_to_dict(row)
        if e["event_date"] < now_date:
            continue
        cat = (request.args.get("category") or "").strip().lower()
        if cat and e["category"].lower() != cat:
            continue
        q = (request.args.get("q") or "").strip().lower()
        if q and q not in (e["title"] + " " + e["description"] + " " +
                           e["category"] + " " + ",".join(e["tags"])).lower():
            continue
        date_f = (request.args.get("date") or "").strip()
        if date_f and e["event_date"] != date_f:
            continue
        e["registrationOpen"] = registration_open(e)
        out.append(e)
    return jsonify(events=out)


@bp.get("/api/events/<int:event_id>")
def get_event(event_id):
    row = db.query_one(
        "SELECT * FROM events WHERE id=? AND status='published'", (event_id,))
    if not row:
        return jsonify(error="event not found"), 404
    e = event_to_dict(row)
    e["registrationOpen"] = registration_open(e)
    user = load_session_user()
    if user:
        reg = db.query_one(
            "SELECT registration_status FROM event_registrations "
            "WHERE event_id=? AND student_user_id=?",
            (event_id, user["id"]))
        e["myRegistration"] = dict(reg) if reg else None
    return jsonify(event=e)
