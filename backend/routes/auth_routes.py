"""Auth routes: student register/login/logout, admin login (spec section 10)."""
from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify, request, session

import db
from auth_service import (auth_required, load_session_user, login_admin,
                          login_student, register_student)

bp = Blueprint("auth", __name__)


def _start_session(uid: int) -> None:
    session.clear()
    session["uid"] = uid
    session.permanent = True


@bp.post("/api/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    uid, err = register_student(data.get("email"), data.get("password"))
    if err:
        return jsonify(error=err), (409 if "already" in err else 400)
    _start_session(uid)
    user = db.query_one("SELECT id, email, role FROM users WHERE id=?", (uid,))
    return jsonify(user=dict(user)), 201


@bp.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email, password = data.get("email"), data.get("password")
    if not email or not password:
        return jsonify(error="email and password required"), 400

    # Admin check first (separate credentials from students, spec section 2).
    if login_admin(email, password):
        admin = db.query_one(
            "SELECT id, email, role FROM users WHERE email=? AND role='admin'",
            ((email or "").strip().lower(),))
        _start_session(admin["id"])
        return jsonify(user=dict(admin))

    uid = login_student(email, password)
    if not uid:
        return jsonify(error="invalid email or password"), 401
    _start_session(uid)
    return jsonify(user=dict(db.query_one(
        "SELECT id, email, role FROM users WHERE id=?", (uid,))))


@bp.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@bp.get("/api/me")
def me():
    user = load_session_user()
    if not user:
        return jsonify(user=None), 200
    return jsonify(user=dict(user))
