"""API integration tests (Flask test client, in-memory backend)."""
from tests.conftest import (create_event, make_admin, make_student)


def test_health(client):
    assert client.get("/api/health").status_code == 200


def test_demo_login_creates_profile(client):
    res = client.post("/api/auth/demo-login", json={"uid": "s1", "name": "Test"})
    assert res.status_code == 200
    assert res.get_json()["user"]["uid"] == "s1"


def test_me_requires_token(client):
    assert client.get("/api/me").status_code == 401


def test_update_interests(client):
    token = make_student(client, "s1", interests=["music", "arts"])
    res = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert res.get_json()["user"]["interests"] == ["music", "arts"]


def test_interests_validation(client):
    token = make_student(client)
    res = client.put("/api/profile/interests",
                     headers={"Authorization": f"Bearer {token}"},
                     json={"interests": "not-a-list"})
    assert res.status_code == 400


def test_admin_only_endpoints_reject_students(client):
    student = make_student(client)
    res = client.post("/api/admin/events",
                      headers={"Authorization": f"Bearer {student}"}, json={})
    assert res.status_code == 403
    # unauthenticated requests are also refused (403 here: valid token format,
    # but verify fails → treated as not admin)


def test_admin_create_publish_cancel(client):
    admin = make_admin(client)
    event = create_event(client, admin)
    event_id = event["eventId"]

    # edit
    res = client.put(f"/api/admin/events/{event_id}",
                     headers={"Authorization": f"Bearer {admin}"},
                     json={"venue": "Hall B"})
    assert res.get_json()["event"]["venue"] == "Hall B"

    # cancel → excluded from public list
    client.post(f"/api/admin/events/{event_id}/cancel",
                headers={"Authorization": f"Bearer {admin}"})
    public = client.get("/api/events").get_json()["events"]
    assert all(e["eventId"] != event_id for e in public)


def test_create_event_validation(client):
    admin = make_admin(client)
    res = client.post("/api/admin/events",
                      headers={"Authorization": f"Bearer {admin}"},
                      json={"title": "No date", "capacity": 5,
                            "category": "chat: coding"})
    assert res.status_code == 400
    res = client.post("/api/admin/events",
                      headers={"Authorization": f"Bearer {admin}"},
                      json={"title": "Bad capacity", "date": "2026-10-20",
                            "capacity": -1, "category": "coding"})
    assert res.status_code == 400


def test_public_events_filters(client):
    admin = make_admin(client)
    create_event(client, admin, category="music", date="2026-11-01")
    create_event(client, admin, category="coding", date="2026-11-02")

    all_events = client.get("/api/events").get_json()["events"]
    assert len(all_events) == 2

    music = client.get("/api/events?category=music").get_json()["events"]
    assert len(music) == 1 and music[0]["category"] == "music"

    by_date = client.get("/api/events?date=2026-11-01").get_json()["events"]
    assert len(by_date) == 1


def test_recommendations_match_interests(client):
    admin = make_admin(client)
    create_event(client, admin, event_id=None)  # e-test coding event
    create_event(client, admin, event_id=None, category="sports",
                 tags=["football"], title="Football match")

    student = make_student(client, "s1", interests=["coding"])
    recs = client.get("/api/recommendations",
                      headers={"Authorization": f"Bearer {student}"}).get_json()
    cats = [r["event"]["category"] for r in recs["recommendations"]]
    assert cats == ["coding"]


def test_register_and_duplicate_prevention(client):
    admin = make_admin(client)
    event = create_event(client, admin)
    eid = event["eventId"]
    student = make_student(client)

    first = client.post(f"/api/events/{eid}/register",
                        headers={"Authorization": f"Bearer {student}"})
    assert first.status_code == 201

    dup = client.post(f"/api/events/{eid}/register",
                      headers={"Authorization": f"Bearer {student}"})
    assert dup.status_code == 409

    my = client.get("/api/my-registrations",
                    headers={"Authorization": f"Bearer {student}"}).get_json()
    assert len(my["registrations"]) == 1
    assert my["registrations"][0]["event"]["eventId"] == eid


def test_capacity_enforced(client):
    admin = make_admin(client)
    event = create_event(client, admin, capacity=1)
    eid = event["eventId"]

    t1 = make_student(client, "s1")
    t2 = make_student(client, "s2")
    assert client.post(f"/api/events/{eid}/register",
                       headers={"Authorization": f"Bearer {t1}"}).status_code == 201
    assert client.post(f"/api/events/{eid}/register",
                       headers={"Authorization": f"Bearer {t2}"}).status_code == 400


def test_registration_deadline_enforced(client):
    admin = make_admin(client)
    event = create_event(client, admin, registrationDeadline="2026-01-01")
    eid = event["eventId"]
    student = make_student(client)
    res = client.post(f"/api/events/{eid}/register",
                      headers={"Authorization": f"Bearer {student}"})
    assert res.status_code == 400
    assert "deadline" in res.get_json()["error"]


def test_cancel_registration_frees_seat(client):
    admin = make_admin(client)
    event = create_event(client, admin, capacity=1)
    eid = event["eventId"]
    s1, s2 = make_student(client, "s1"), make_student(client, "s2")

    client.post(f"/api/events/{eid}/register", headers={"Authorization": f"Bearer {s1}"})
    # full now → s2 rejected
    assert client.post(f"/api/events/{eid}/register",
                       headers={"Authorization": f"Bearer {s2}"}).status_code == 400
    # s1 cancels → s2 can register
    client.post(f"/api/events/{eid}/cancel-registration",
                headers={"Authorization": f"Bearer {s1}"})
    assert client.post(f"/api/events/{eid}/register",
                       headers={"Authorization": f"Bearer {s2}"}).status_code == 201
