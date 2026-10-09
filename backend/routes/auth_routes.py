"""Auth routes: demo sign-in for dev mode."""
from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify, request

from auth_service import auth_required, create_demo_token

bp = Blueprint("auth", __name__)


@bp.post("/api/auth/demo-login")
def demo_login():
    """Dev-mode sign-in: creates or fetches a user profile and returns a token."""
    data = request.get_json(silent=True) or {}
    uid = (data.get("uid") or "").strip()
    name = (data.get("name") or "").strip()
    if not uid:
        return jsonify(error="uid required"), 400

    user = current_app.store.get_user(uid)
    if not user:
        user = current_app.store.add_user(uid, {
            "name": name or uid,
            "department": data.get("department", ""),
            "year": data.get("year", ""),
            "interests": [],
            "isAdmin": bool(data.get("isAdmin", False)),
        })
    elif name:
        user = current_app.store.update_user(uid, {"name": name})

    return jsonify(token=create_demo_token(uid), user=user)


@bp.get("/api/me")
@auth_required()
def me():
    return jsonify(user=current_app.store.get_user(g.uid))
