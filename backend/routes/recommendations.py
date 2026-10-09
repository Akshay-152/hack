"""Recommendations endpoint (PLAN API section 9)."""
from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify

from auth_service import auth_required
from services.recommender import ScoringWeights, recommend

bp = Blueprint("recommendations", __name__)


@bp.get("/api/recommendations")
@auth_required()
def get_recommendations():
    user = current_app.store.get_user(g.uid)
    if not user:
        return jsonify(error="profile not found"), 404

    events = current_app.store.list_events()
    now = __import__("storage").utcnow()
    ranked = recommend(user, events, now, ScoringWeights(
        category_match=current_app.config["WEIGHT_CATEGORY_MATCH"],
        tag_match=current_app.config["WEIGHT_TAG_MATCH"],
        audience_relevance=current_app.config["WEIGHT_AUDIENCE_RELEVANCE"],
        registration_open=current_app.config["WEIGHT_REGISTRATION_OPEN"],
    ))

    return jsonify(recommendations=[
        {"score": r["score"], "event": r["event"]} for r in ranked
    ])
