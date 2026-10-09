"""Recommendation engine: transparent rule-based scoring (PLAN 6.3)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


def naive_utc_now() -> datetime:
    """Naive UTC datetime, comparable with naive ISO-parsed event dates."""
    from datetime import timezone
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class ScoringWeights:
    category_match: int = 3
    tag_match: int = 2
    audience_relevance: int = 1
    registration_open: int = 1


def event_is_past(event: dict, now: datetime) -> bool:
    date = event.get("date") or ""
    end = event.get("endTime") or "23:59"
    try:
        end_dt = datetime.fromisoformat(f"{date}T{end}")
    except ValueError:
        return False
    return end_dt < now


def is_registration_open(event: dict, now: datetime) -> bool:
    deadline = event.get("registrationDeadline")
    if deadline:
        try:
            if datetime.fromisoformat(deadline) < now:
                return False
        except ValueError:
            pass
    has_space = event.get("registeredCount", 0) < event.get("capacity", 0)
    return has_space


def score_event(event: dict, user: dict, weights: ScoringWeights,
                now: datetime) -> int | None:
    """Return match score, or None if the event must be excluded.

    Exclusion rules: not published, cancelled, or already past.
    """
    if event.get("status") != "published":
        return None
    if event_is_past(event, now):
        return None

    user_interests = set(i.lower() for i in user.get("interests", []))
    score = 0
    if event.get("category", "").lower() in user_interests:
        score += weights.category_match

    tags = set(t.lower() for t in event.get("tags", []))
    for tag in tags & user_interests:
        score += weights.tag_match

    audience = [str(a).lower() for a in event.get("targetAudience", [])]
    if user.get("department", "").lower() in audience:
        score += weights.audience_relevance
    year = str(user.get("year", ""))
    if year and year in audience:
        score += weights.audience_relevance

    if is_registration_open(event, now):
        score += weights.registration_open

    return score


def recommend(user: dict, events: list[dict], now: datetime,
              weights: ScoringWeights) -> list[dict]:
    """Rank published, upcoming events for a user.

    Excludes zero-interest events only when the user has interests at
    all; brand-new users still get upcoming events sorted by date.
    """
    has_interests = bool(user.get("interests"))
    scored = []
    for event in events:
        score = score_event(event, user, weights, now)
        if score is None:
            continue
        scored.append({"score": score, "event": event})

    if has_interests:
        scored = [s for s in scored if s["score"] > weights.registration_open]

    scored.sort(key=lambda s: (-s["score"], s["event"].get("date", ""),
                               s["event"].get("startTime", "")))
    return scored
