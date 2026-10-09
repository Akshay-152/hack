"""Student profile endpoints (PLAN API section 9)."""
from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify, request

from auth_service import auth_required

bp = Blueprint("profile", __name__)

ALLOWED_FIELDS = {"name", "department", "year", "interests"}


@bp.get("/api/profile")
@auth_required()
def get_profile():
    user = current_app.store.get_user(g.uid)
    if not user:
        return jsonify(error="profile not found"), 404
    return jsonify(user=user)


@bp.put("/api/profile/interests")
@auth_required()
def update_interests():
    data = request.get_json(silent=True) or {}
    interests = data.get("interests")
    if not isinstance(interests, list) or not all(isinstance(i, str) for i in interests):
        return jsonify(error="interests must be a list of strings"), 400
    if len(interests) > 20:
        return jsonify(error="too many interests (max 20)"), 400

    user = current_app.store.update_user(g.uid, {"interests": interests})
    if not user:
        return jsonify(error="profile not found"), 404
    return jsonify(user=user)


@bp.put("/api/profile")
@auth_required()
def update_profile():
    data = request.get_json(silent=True) or {}
    updates = {k: v for k, v in data.items() if k in ALLOWED_FIELDS}
    if not updates:
        return jsonify(error="no updatable fields provided"), 400
    if "interests" in updates and not isinstance(updates["interests"], list):
        return jsonify(error="interests must be a list of strings"), 400

    user = current_app.store.update_user(g.uid, updates)
    if not user:
        return jsonify(error="profile not found"), 404
    return jsonify(user=user)
