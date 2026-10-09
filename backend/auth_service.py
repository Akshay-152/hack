"""Session-cookie authentication.

Students: email + password (werkzeug hash) stored in `users`.
Admin: development credentials from config (default admin/admin) as a
`users` row with role='admin', seeded at first boot — dev only, never
plain-text storage, replace ADMIN_* env vars in production.
"""
from __future__ import annotations

import functools
import os

from flask import current_app, g, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

import db

EMAIL_RE = __import__("re").compile(
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def seed_admin() -> None:
    """Ensure the config-admin exists (dev credentials, hash stored)."""
    username = os.getenv("ADMIN_USERNAME",
                         current_app.config.get("ADMIN_USERNAME", "admin")
                         if current_app else "admin")
    password = os.getenv("ADMIN_PASSWORD",
                         current_app.config.get("ADMIN_PASSWORD", "admin")
                         if current_app else "admin")
    row = db.query_one("SELECT id FROM users WHERE email = ?", (username,))
    if not row:
        db.execute(
            "INSERT INTO users (email, password_hash, role, created_at) "
            "VALUES (?,?,?,?)",
            (username, generate_password_hash(password), "admin", db.now_iso()))


def login_admin(username: str, password: str) -> bool:
    row = db.query_one(
        "SELECT * FROM users WHERE email = ? AND role = 'admin'", (username,))
    return bool(row and check_password_hash(row["password_hash"], password))


def register_student(email: str, password: str) -> tuple[int | None, str]:
    """Returns (user_id, error). Hashes the password; blocks duplicates."""
    email = (email or "").strip().lower()
    if not EMAIL_RE.match(email):
        return None, "invalid email address"
    if len(password or "") < 6:
        return None, "password must be at least 6 characters"
    if db.query_one("SELECT id FROM users WHERE email = ?", (email,)):
        return None, "email already registered"
    uid = db.execute(
        "INSERT INTO users (email, password_hash, role, created_at) "
        "VALUES (?,?, 'student', ?)",
        (email, generate_password_hash(password), db.now_iso()))
    db.execute("INSERT INTO student_profiles (user_id) VALUES (?)", (uid,))
    return uid, ""


def login_student(email: str, password: str) -> int | None:
    row = db.query_one(
        "SELECT * FROM users WHERE email = ? AND role = 'student'",
        ((email or "").strip().lower(),))
    return row["id"] if row and check_password_hash(row["password_hash"],
                                                    password or "") else None


def load_session_user():
    uid = session.get("uid")
    if not uid:
        return None
    return db.query_one(
        "SELECT id, email, role FROM users WHERE id = ?", (uid,))


def auth_required(require_admin: bool = False):
    """Attach g.user (sqlite Row) or return 401/403 JSON."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            user = load_session_user()
            if not user:
                return jsonify(error="login required"), 401
            if require_admin and user["role"] != "admin":
                return jsonify(error="admin access required"), 403
            g.user = user
            return fn(*args, **kwargs)
        return wrapper
    return decorator
