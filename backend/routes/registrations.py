"""Registration endpoints (spec section 5).

Internal registration: validated + stored here (dedup by unique index,
capacity and deadline enforced server-side). External: stored as
pending_external — completion of a Google Form etc. can't be verified.
"""
from __future__ import annotations

from flask import Blueprint, g, jsonify

from auth_service import auth_required
import db
from helpers import event_to_dict, registration_open

bp = Blueprint("registrations", __name__)


@bp.post("/api/events/<int:event_id>/register")
@auth_required()
def register(event_id):
    if g.user["role"] != "student":
        return jsonify(error="admin accounts cannot register for events"), 403

    row = db.query_one("SELECT * FROM events WHERE id=?", (event_id,))
    if not row:
        return jsonify(error="event not found"), 404
    e = event_to_dict(row)

    if e["status"] == "cancelled":
        return jsonify(error="this event has been cancelled"), 400
    if e["status"] != "published":
        return jsonify(error="event is not open for registration"), 400
    if row["event_date"] < db.now_iso()[:10]:
        return jsonify(error="event already ended"), 400

    dup = db.query_one(
        "SELECT id FROM event_registrations "
        "WHERE event_id=? AND student_user_id=?",
        (event_id, g.user["id"]),)
    if dup:
        return jsonify(error="already registered for this event"), 409

    if not registration_open(e):
        return jsonify(error="registration is closed "
                             "(event full or deadline passed)"), 400

    method = "external" if e["registration_type"] == "external" else "internal"
    status = "pending_external" if method == "external" else "registered"

    try:
        db.execute(
            "INSERT INTO event_registrations "
            "(event_id, student_user_id, registration_status, registered_at) "
            "VALUES (?,?,?,?)",
            (event_id, g.user["id"], status, db.now_iso()))
    except Exception:
        return jsonify(error="already registered for this event"), 409

    message = {
        "internal": "Registration successful 🎉",
        "external": "External registration: your spot is tracked as pending "
                    "until you complete the form.",
    }[method]
    return jsonify(registration={"eventId": event_id, "method": method,
                                 "status": status, "message": message}), 201


@bp.post("/api/events/<int:event_id>/cancel-registration")
@auth_required()
def cancel(event_id):
    row = db.query_one(
        "SELECT id FROM event_registrations "
        "WHERE event_id=? AND student_user_id=?",
        (event_id, g.user["id"]))
    if not row:
        return jsonify(error="no registration found"), 404
    db.execute("DELETE FROM event_registrations WHERE id=?", (row["id"],))
    return jsonify(ok=True)


@bp.get("/api/my-registrations")
@auth_required()
def my_registrations():
    rows = db.query(
        "SELECT r.id AS reg_id, r.registration_status, r.registered_at, "
        "e.id AS eid, e.title, e.description, e.category, e.poster_path, "
        "e.event_date, e.start_time, e.end_time, e.venue, e.organizer, "
        "e.registration_deadline, e.capacity, e.registration_type, "
        "e.registration_url, e.registration_instructions, e.tags, e.status "
        "FROM event_registrations r JOIN events e ON e.id = r.event_id "
        "WHERE r.student_user_id=? ORDER BY r.registered_at DESC",
        (g.user["id"],))
    out = []
    for row in rows:
        r = dict(row)
        reg = {"id": r.pop("reg_id"),
               "status": r.pop("registration_status"),
               "registeredAt": r.pop("registered_at")}
        r["id"] = r.pop("eid")
        out.append({"registration": reg, "event": event_to_dict(r)})
    return jsonify(registrations=out)
