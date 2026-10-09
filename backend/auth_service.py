"""Authentication helpers.

In dev (memory) mode a simple signed demo-token scheme is used so the
app runs without external services. With Firebase configured, ID
tokens issued by Firebase Auth are verified with firebase_admin.
"""
from __future__ import annotations

import functools
import hmac
import time

from flask import current_app, g, jsonify, request

DEMO_KEY = "campus-bot-demo"  # '%(demo)s' token signature key (dev only)

MAX_SKEW = 5 * 60  # seconds


def _sign(payload: str) -> str:
    key = (current_app.config["SECRET_KEY"] + DEMO_KEY).encode()
    return hmac.new(key, payload.encode(), "sha256").hexdigest()


def create_demo_token(uid: str) -> str:
    """Create a dev-only token '%(uid)s:%(ts)s:%(sig)s' (memory backend)."""
    issued = str(int(time.time()))
    payload = f"{uid}:{issued}"
    return f"{payload}:{_sign(payload)}"


def verify_token(token: str) -> str | None:
    """Return the uid for a valid token, else None."""
    if not token:
        return None
    parts = token.split(":")
    if len(parts) != 3:
        return None
    uid, issued, sig = parts
    payload = f"{uid}:{issued}"
    if not hmac.compare_digest(_sign(payload), sig):
        return None
    try:
        issued_at = int(issued)
    except ValueError:
        return None
    if abs(time.time() - issued_at) > 365 * 24 * 3600:
        return None  # very old token; dev tokens are long-lived but not forever
    return uid


def firebase_verify(firebase_token: str) -> str | None:
    """Verify a Firebase ID token when firebase-admin is configured."""
    try:
        from firebase_admin import auth as fb_auth
        decoded = fb_auth.verify_id_token(firebase_token)
        return decoded.get("uid")
    except Exception:
        return None


def auth_required(require_admin: bool = False):
    """Decorator: attach g.uid; optionally enforce admin role."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            header = request.headers.get("Authorization", "")
            token = header[7:].strip() if header.startswith("Bearer ") else ""
            if require_admin:
                uid = verify_token(token) or firebase_verify(token)
                user = current_app.store.get_user(uid) if uid else None
                if not uid or not user or not user.get("isAdmin"):
                    return jsonify(error="admin access required"), 403
            else:
                uid = verify_token(token)
                if not uid:
                    return jsonify(error="authentication required"), 401
            g.uid = uid
            return fn(*args, **kwargs)
        return wrapper
    return decorator
