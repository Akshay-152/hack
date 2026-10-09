"""Student profile endpoints (spec section 3)."""
from __future__ import annotations

import os
import uuid
from flask import Blueprint, current_app, g, jsonify, request

import db
from auth_service import auth_required

bp = Blueprint("profile", __name__)

PROFILE_FIELDS = ["full_name", "college_id", "course", "department",
                  "semester", "interests", "preferred_categories"]
MAX_PHOTO_SIZE = 3 * 1024 * 1024
ALLOWED_PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp"}


@bp.get("/api/profile")
@auth_required()
def get_profile():
    row = db.query_one(
        "SELECT p.*, u.email FROM student_profiles p "
        "JOIN users u ON u.id = p.user_id WHERE p.user_id = ?", (g.user["id"],))
    if not row:
        return jsonify(error="profile not found"), 404
    return jsonify(profile=dict(row))


@bp.put("/api/profile")
@auth_required()
def update_profile():
    data = request.get_json(silent=True) or {}
    updates = {}
    for f in PROFILE_FIELDS:
        v = data.get(f)
        if v is None:
            continue
        updates[f] = ",".join(str(x).strip() for x in v) if isinstance(v, list) \
                     else str(v).strip()
    if not updates:
        return jsonify(error="no updatable fields provided"), 400

    existing = db.query_one(
        "SELECT id FROM student_profiles WHERE user_id=?", (g.user["id"],))
    if existing:
        set_clause = ", ".join(f"{k}=?" for k in updates)
        db.execute(f"UPDATE student_profiles SET {set_clause} WHERE user_id=?",
                   (*updates.values(), g.user["id"]))
    else:
        cols = ", ".join(updates)
        ph = ", ".join("?" * len(updates))
        db.execute(f"INSERT INTO student_profiles (user_id, {cols}) "
                   f"VALUES (?, {ph})", (g.user["id"], *updates.values()))
    return jsonify(profile=dict(db.query_one(
        "SELECT * FROM student_profiles WHERE user_id=?", (g.user["id"],))))


@bp.post("/api/profile/photo")
@auth_required()
def upload_photo():
    f = request.files.get("photo")
    if not f or not f.filename:
        return jsonify(error="photo file required"), 400
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED_PHOTO_EXT:
        return jsonify(error="image must be jpg, png, or webp"), 400
    blob = f.read()
    if len(blob) > MAX_PHOTO_SIZE:
        return jsonify(error="image too large (max 3MB)"), 400

    fname = f"u{g.user['id']}_{uuid.uuid4().hex[:8]}{ext}"
    f.stream.seek(0)
    f.save(os.path.join(current_app.config["UPLOAD_DIR"], fname))
    db.execute("UPDATE student_profiles SET profile_photo=? WHERE user_id=?",
               (fname, g.user["id"]))
    return jsonify(photoUrl=f"/uploads/{fname}")
