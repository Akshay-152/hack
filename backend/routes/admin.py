"""Admin-only event CRUD with poster upload (spec section 4)."""
from __future__ import annotations

import os
import uuid

from flask import Blueprint, current_app, g, jsonify, request

import db
from auth_service import auth_required
from helpers import valid_date, valid_time

bp = Blueprint("admin", __name__)

MAX_POSTER_SIZE = 5 * 1024 * 1024
ALLOWED_POSTER_EXT = {".jpg", ".jpeg", ".png", ".webp"}

EVENT_FIELDS = ["title", "description", "category", "event_date", "start_time",
                "end_time", "venue", "organizer", "registration_deadline",
                "capacity", "registration_type", "registration_url",
                "registration_instructions", "tags", "status"]


def validate_payload(data: dict, *, partial: bool = False) -> str | None:
    for f in ("title", "category", "event_date"):
        if not partial and not data.get(f):
            return f"missing required field: {f}"
    if "event_date" in data and not valid_date(data["event_date"]):
        return "event_date must be a valid date (YYYY-MM-DD)"
    for field in ("start_time", "end_time", "registration_deadline"):
        if data.get(field):
            if field.endswith("time") and not valid_time(data[field]):
                return f"{field} must be HH:MM"
            if field.endswith("deadline") and not valid_date(data[field]):
                return "registration_deadline must be a valid date (YYYY-MM-DD)"
    if "capacity" in data:
        cap = data["capacity"]
        if not isinstance(cap, int) or cap < 0:
            return "capacity must be a non-negative integer"
    if "status" in data and data["status"] not in (
            "draft", "published", "cancelled"):
        return "status must be draft, published, or cancelled"
    if "registration_type" in data and data["registration_type"] not in (
            "internal", "external", "both"):
        return "registration_type must be internal, external, or both"
    if data.get("registration_type") == "external" and not data.get(
            "registration_url"):
        return "external registration requires registration_url"
    return None


def clean_payload(data: dict) -> dict:
    out = {}
    for f in EVENT_FIELDS:
        if f in data:
            v = data[f]
            if isinstance(v, list):
                v = ",".join(str(x).strip() for x in v if str(x).strip())
            out[f] = v
    return out


def save_poster(file_storage) -> str | tuple[str, int]:
    ext = os.path.splitext(file_storage.filename)[1].lower()
    if ext not in ALLOWED_POSTER_EXT:
        return "", "poster must be jpg, png, or webp", 400
    blob = file_storage.read()
    if len(blob) > MAX_POSTER_SIZE:
        return "", "poster too large (max 5MB)", 400
    fname = f"e{uuid.uuid4().hex[:10]}{ext}"
    file_storage.stream.seek(0)
    file_storage.save(os.path.join(current_app.config["UPLOAD_DIR"], fname))
    return fname, None, None


@bp.get("/api/admin/events")
@auth_required(require_admin=True)
def admin_list_events():
    from helpers import event_to_dict
    rows = db.query(
        "SELECT e.*, COUNT(r.id) AS reg_count FROM events e "
        "LEFT JOIN event_registrations r "
        "  ON r.event_id = e.id AND r.registration_status != 'cancelled' "
        "GROUP BY e.id ORDER BY e.event_date")
    # reg_count column stripped: event_to_dict counts seats itself.
    out = []
    for row in rows:
        d = dict(row)
        d.pop("reg_count", None)
        out.append(event_to_dict(d))
    return jsonify(events=out)


@bp.post("/api/admin/events")
@auth_required(require_admin=True)
def create_event():
    data = request.form.to_dict() if request.files else (
        request.get_json(silent=True) or {})
    if request.files:
        data["capacity"] = int(data.get("capacity") or 0)
    err = validate_payload(data)
    if err:
        return jsonify(error=err), 400

    poster = ""
    if request.files and request.files.get("poster") and request.files["poster"].filename:
        poster, perr, pcode = save_poster(request.files["poster"])
        if perr:
            return jsonify(error=perr), pcode

    eid = db.execute(
        "INSERT INTO events (title, description, category, poster_path, "
        "event_date, start_time, end_time, venue, organizer, "
        "registration_deadline, capacity, registration_type, registration_url, "
        "registration_instructions, tags, status, created_by, created_at, "
        "updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (data.get("title"), data.get("description", ""),
         data.get("category"), poster, data.get("event_date"),
         data.get("start_time", ""), data.get("end_time", ""),
         data.get("venue", ""), data.get("organizer", ""),
         data.get("registration_deadline", ""), data.get("capacity", 0),
         data.get("registration_type", "internal"),
         data.get("registration_url", ""),
         data.get("registration_instructions", ""),
         data.get("tags", ""),
         data.get("status", "draft"), g.user["id"],
         db.now_iso(), db.now_iso()))
    from helpers import event_to_dict
    return jsonify(event=event_to_dict(db.query_one(
        "SELECT * FROM events WHERE id=?", (eid,)))), 201


@bp.put("/api/admin/events/<int:event_id>")
@auth_required(require_admin=True)
def update_event(event_id):
    row = db.query_one("SELECT * FROM events WHERE id=?", (event_id,))
    if not row:
        return jsonify(error="event not found"), 404
    data = request.form.to_dict() if request.files else (
        request.get_json(silent=True) or {})
    if request.files and data.get("capacity"):
        data["capacity"] = int(data.get("capacity") or 0)
    err = validate_payload(data, partial=True)
    if err:
        return jsonify(error=err), 400

    updates = clean_payload(data)
    if request.files and request.files.get("poster") and request.files["poster"].filename:
        poster, perr, pcode = save_poster(request.files["poster"])
        if perr:
            return jsonify(error=perr), pcode
        old = row["poster_path"]
        if old:
            try:
                os.remove(os.path.join(current_app.config["UPLOAD_DIR"], old))
            except OSError:
                pass
        updates["poster_path"] = poster

    if updates:
        set_clause = ", ".join(f"{k}=?" for k in updates)
        db.execute(
            f"UPDATE events SET {set_clause}, updated_at=? WHERE id=?",
            (*updates.values(), db.now_iso(), event_id))
    from helpers import event_to_dict
    return jsonify(event=event_to_dict(db.query_one(
        "SELECT * FROM events WHERE id=?", (event_id,))))


@bp.delete("/api/admin/events/<int:event_id>")
@auth_required(require_admin=True)
def delete_event(event_id):
    row = db.query_one("SELECT * FROM events WHERE id=?", (event_id,))
    if not row:
        return jsonify(error="event not found"), 404
    db.execute("DELETE FROM event_registrations WHERE event_id=?", (event_id,))
    db.execute("DELETE FROM events WHERE id=?", (event_id,))
    if row["poster_path"]:
        try:
            os.remove(os.path.join(current_app.config["UPLOAD_DIR"],
                                   row["poster_path"]))
        except OSError:
            pass
    return jsonify(ok=True, deletedRegistrations=True)
