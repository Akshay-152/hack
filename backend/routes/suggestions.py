"""Event suggestions (spec section 6)."""
from __future__ import annotations

from flask import Blueprint, g, jsonify, request

import db
from auth_service import auth_required
from helpers import CATEGORIES, valid_date

bp = Blueprint("suggestions", __name__)


@bp.post("/api/event-suggestions")
@auth_required()
def submit_suggestion():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    category = (data.get("category") or "").strip().lower()
    if len(title) < 3:
        return jsonify(error="title must be at least 3 characters"), 400
    if category not in CATEGORIES:
        return jsonify(error="invalid category"), 400
    if data.get("preferredDate") and not valid_date(data["preferredDate"]):
        return jsonify(error="preferredDate must be a valid date"), 400

    sid = db.execute(
        "INSERT INTO event_suggestions "
        "(student_user_id, title, category, description, preferred_date, "
        " reason, status, created_at) VALUES (?,?,?,?,?,?, 'pending', ?)",
        (g.user["id"], title, category,
         (data.get("description") or "").strip(),
         data.get("preferredDate") or "",
         (data.get("reason") or "").strip(),
         db.now_iso()))
    return jsonify(suggestion={"id": sid, "status": "pending"}), 201


@bp.get("/api/event-suggestions")
@auth_required()
def my_suggestions():
    rows = db.query(
        "SELECT * FROM event_suggestions WHERE student_user_id=? "
        "ORDER BY created_at DESC", (g.user["id"],))
    return jsonify(suggestions=[dict(r) for r in rows])


@bp.get("/api/admin/suggestions")
@auth_required(require_admin=True)
def admin_all_suggestions():
    rows = db.query(
        "SELECT s.*, u.email AS student_email FROM event_suggestions s "
        "JOIN users u ON u.id = s.student_user_id "
        "ORDER BY s.created_at DESC")
    return jsonify(suggestions=[dict(r) for r in rows])


@bp.post("/api/admin/suggestions/<int:sid>/<action>")
@auth_required(require_admin=True)
def review_suggestion(sid, action):
    if action not in ("approve", "reject"):
        return jsonify(error="action must be approve or reject"), 400
    row = db.query_one("SELECT id FROM event_suggestions WHERE id=?", (sid,))
    if not row:
        return jsonify(error="suggestion not found"), 404
    status = "approved" if action == "approve" else "rejected"
    db.execute("UPDATE event_suggestions SET status=? WHERE id=?", (status, sid))
    return jsonify(suggestion={"id": sid, "status": status})
