"""Unit tests for the recommendation engine (PLAN section 6.3 rules)."""
from datetime import datetime

import pytest

from services.recommender import ScoringWeights, recommend, score_event

NOW = datetime(2026, 10, 9, 12, 0, 0)
W = ScoringWeights()


def make_event(**overrides):
    base = {
        "eventId": "e1", "title": "Hackathon", "category": "coding",
        "tags": ["hackathon", "python"], "date": "2026-10-20",
        "startTime": "10:00", "endTime": "16:00",
        "capacity": 100, "registeredCount": 10,
        "status": "published", "targetAudience": [],
    }
    base.update(overrides)
    return base


def make_user(**overrides):
    base = {"uid": "s1", "department": "CSE", "year": "2",
            "interests": ["coding", "python"]}
    base.update(overrides)
    return base


def test_category_match_scores_3():
    score = score_event(make_event(), make_user(), W, NOW)
    # category(+3) + tag 'python'(+2) + open registration(+1) = 6
    assert score == 6


def test_each_matching_tag_scores_2():
    event = make_event(tags=["coding", "python", "hackathon"])
    score = score_event(event, make_user(), W, NOW)
    # category(+3) + 2 tags(*2 = +4) + open(+1) = 8
    assert score == 8


def test_audience_relevance_scores_1():
    event = make_event(targetAudience=["CSE"])
    score = score_event(event, make_user(), W, NOW)
    # 6 + department(+1) = 7
    assert score == 7


def test_cancelled_event_excluded():
    assert score_event(make_event(status="cancelled"), make_user(), W, NOW) is None


def test_draft_event_excluded():
    assert score_event(make_event(status="draft"), make_user(), W, NOW) is None


def test_past_event_excluded():
    assert score_event(make_event(date="2026-10-01"), make_user(), W, NOW) is None


def test_registration_closed_no_open_bonus():
    event = make_event(registeredCount=100)  # full
    score = score_event(event, make_user(), W, NOW)
    # no open-registration bonus: 6 - 1 = 5
    assert score == 5


def test_recommend_sorts_by_score_then_date():
    user = make_user()
    # No open-registration bonus here (capacity full) so scores are pure:
    # category(3) + matching tags(2 each). 'equal' sorts before 'high' at the
    # same score because its date is earlier.
    events = [
        make_event(eventId="low", tags=[], registeredCount=100,
                   date="2026-10-15"),                          # 3
        make_event(eventId="high", tags=["python"], registeredCount=100,
                   date="2026-10-30"),                         # 5
        make_event(eventId="equal", tags=["python"], registeredCount=100,
                   date="2026-10-12"),                         # 5
    ]
    ranked = recommend(user, events, NOW, W)
    ids = [r["event"]["eventId"] for r in ranked]
    assert ids == ["equal", "high", "low"]
    assert ranked[0]["score"] == ranked[1]["score"] == 5
    assert ranked[2]["score"] == 3


def test_recommend_excludes_irrelevant_when_user_has_interests():
    user = make_user(interests=["music"])
    events = [make_event(eventId="coding_e")]
    ranked = recommend(user, events, NOW, W)
    # score = open-registration only (1) → below interest bar → excluded
    assert all(r["event"]["eventId"] != "coding_e" for r in ranked)


def test_new_user_without_interests_still_sees_events():
    user = make_user(interests=[])
    events = [make_event()]
    ranked = recommend(user, events, NOW, W)
    assert len(ranked) == 1
