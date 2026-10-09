"""Shared helpers: validation, serialization."""
from __future__ import annotations

from datetime import datetime

import db

CATEGORIES = ["coding", "ai", "sports", "music", "arts",
              "entrepreneurship", "volunteering"]


def valid_date(value: str) -> bool:
    try:
        datetime.fromisoformat(value)
        return True
    except (ValueError, TypeError):
        return False


def valid_time(value: str) -> bool:
    try:
        datetime.strptime(value, "%H:%M")
        return True
    except (ValueError, TypeError):
        return False


def event_to_dict(row) -> dict:
    """Serialize an events row (dict or sqlite Row) for API output."""
    d = dict(row)
    d["tags"] = [t for t in (d.get("tags") or "").split(",") if t]
    seats_taken = db.query_one(
        "SELECT COUNT(*) AS c FROM event_registrations "
        "WHERE event_id=? AND registration_status != 'cancelled'",
        (d["id"],))["c"]
    d["registeredCount"] = seats_taken
    d["posterUrl"] = f"/uploads/{d['poster_path']}" if d.get("poster_path") else ""
    return d


def serialize_event_full(row) -> dict:
    return event_to_dict(row)


def naive_utcnow() -> datetime:
    return datetime.utcnow()


def registration_open(event: dict) -> bool:
    """Deadline + capacity check on a serialized event dict."""
    if event.get("registeredCount", 0) >= event.get("capacity", 0):
        return False
    dl = event.get("registration_deadline")
    if dl and valid_date(dl):
        if datetime.fromisoformat(dl) < naive_utcnow():
            return False
    return True
