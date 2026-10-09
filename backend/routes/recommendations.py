"""Recommendations endpoint — rule-based scorer over SQLite events."""
from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify

from auth_service import auth_required
import db
from helpers import event_to_dict
from services.recommender import ScoringWeights, naive_utc_now, score_event

bp = Blueprint("recommendations", __name__)


def _build_user(profile) -> dict:
    """Shape the scorer expects (interests/department/year)."""
    interests = [s.strip() for s in
                 ((profile["interests"] if profile else "") or "").split(",")
                 if s.strip()]
    return {
        "uid": g.user["id"],
        "department": (profile["department"] if profile else "") or "",
        "year": str((profile["semester"] if profile else "") or ""),
        "interests": interests,
    }


def _scorer_view(e: dict, deadline: str) -> dict:
    """Adapt an SQLite event dict into the scorer's field names."""
    return {"status": "published",
            "date": e["event_date"],
            "endTime": e["end_time"] or "23:59",
            "category": e["category"],
            "tags": list(e["tags"]),
            "targetAudience": [],
            "registeredCount": e["registeredCount"],
            "capacity": e["capacity"],
            "registrationDeadline": deadline or ""}


@bp.get("/api/recommendations")
@auth_required()
def get_recommendations():
    """Rule-based re-ranking of published upcoming events for this student.

    Matching events are ranked first; non-matching events stay visible
    afterwards (spec section 7: don't hide others). Logic is independent
    of the AI model.
    """
    profile = db.query_one(
        "SELECT * FROM student_profiles WHERE user_id=?", (g.user["id"],))
    rows = db.query(
        "SELECT * FROM events WHERE status='published' "
        "ORDER BY event_date, start_time")
    now = naive_utc_now()
    now_date = db.now_iso()[:10]

    weights = ScoringWeights(
        category_match=current_app.config["WEIGHT_CATEGORY_MATCH"],
        tag_match=current_app.config["WEIGHT_TAG_MATCH"],
        audience_relevance=current_app.config["WEIGHT_AUDIENCE_RELEVANCE"],
        registration_open=current_app.config["WEIGHT_REGISTRATION_OPEN"],
    )
    user = _build_user(profile)

    ranked = []
    for row in rows:
        e = event_to_dict(row)
        if e["event_date"] < now_date:
            continue
        deadline = row["registration_deadline"]
        score = score_event(_scorer_view(e, deadline), user, weights, now)
        if score is None:
            continue
        ranked.append({"score": score, **e})

    ranked.sort(key=lambda e: -e["score"])
    seen = {e["id"] for e in ranked}
    for row in rows:  # unmatched events remain visible below
        other = event_to_dict(row)
        if other["event_date"] >= now_date and other["id"] not in seen:
            ranked.append({"score": 0, **other})
    return jsonify(recommendations=ranked)
