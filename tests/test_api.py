"""API integration tests (Flask test client, SQLite backend per session).

Covers acceptance scenarios from spec section 12."""
from tests.conftest import (create_event, login_admin, login_student,
                            register_student)


def test_health(client):
    assert client.get("/api/health").status_code == 200


def login_and_register_student(client, email="s1@campus.edu"):
    register_student(client, email)
    return login_student(client, email)


# ---- Scenario 1: admin login --------------------------------------------
def test_admin_login_and_separation(client):
    assert login_admin(client)["role"] == "admin"
    # wrong password
    res = client.post("/api/auth/login",
                      json={"email": "admin", "password": "nope"})
    assert res.status_code == 401


# ---- Scenarios 2-4: student register/login/persistence -------------------
def test_student_register_login_persist(client, app):
    register_student(client, "s1@campus.edu")
    client.post("/api/auth/logout")
    # login again after "restart" (fresh client, same DB)
    c2 = app.test_client()
    login_student(c2, "s1@campus.edu")
    assert c2.get("/api/me").get_json()["user"]["email"] == "s1@campus.edu"


def test_duplicate_email_blocked(client):
    register_student(client, "dup@campus.edu")
    res = client.post("/api/auth/register",
                      json={"email": "dup@campus.edu", "password": "secret1"})
    assert res.status_code == 409


def test_invalid_email_rejected(client):
    res = client.post("/api/auth/register",
                      json={"email": "not-an-email", "password": "secret1"})
    assert res.status_code == 400


def test_short_password_rejected(client):
    res = client.post("/api/auth/register",
                      json={"email": "ok@campus.edu", "password": "abc"})
    assert res.status_code == 400


def test_passwords_hashed(client):
    import db
    register_student(client, "hash@campus.edu")
    row = db.query_one("SELECT password_hash FROM users WHERE email=?",
                       ("hash@campus.edu",))
    assert "secret1" not in row["password_hash"]


# ---- Scenario 4: profile persistence -------------------------------------
def test_profile_save_and_reload(client, app):
    login_and_register_student(client)
    res = client.put("/api/profile", json={
        "full_name": "Akshay", "college_id": "C21", "course": "B.Tech",
        "department": "CSE", "semester": "3",
        "interests": ["coding", "ai"], "preferred_categories": ["coding"]})
    assert res.status_code == 200
    c2 = app.test_client()  # fresh session
    login_student(c2)
    profile = c2.get("/api/profile").get_json()["profile"]
    assert profile["full_name"] == "Akshay"
    assert "coding" in profile["interests"]


# ---- Scenarios 5-8: admin CRUD + publishing ------------------------------
def test_admin_crud_and_visibility(client):
    login_admin(client)
    event = create_event(client, status="draft")
    eid = event["id"]

    # draft not visible publicly
    assert all(e["id"] != eid for e in
               client.get("/api/events").get_json()["events"])

    # publish → visible
    client.put(f"/api/admin/events/{eid}", json={"status": "published"})
    assert any(e["id"] == eid for e in
               client.get("/api/events").get_json()["events"])

    # edit
    r = client.put(f"/api/admin/events/{eid}", json={"venue": "Hall B"})
    assert r.get_json()["event"]["venue"] == "Hall B"

    # delete
    assert client.delete(f"/api/admin/events/{eid}").get_json()["ok"]
    assert client.get(f"/api/events/{eid}").status_code == 404


def test_cancelled_events_hidden_from_dashboard(client):
    login_admin(client)
    create_event(client, status="cancelled")
    events = client.get("/api/events").get_json()["events"]
    assert not events


def test_invalid_event_payload_rejected(client):
    login_admin(client)
    assert client.post("/api/admin/events", json={
        "title": "x", "category": "ai", "event_date": "bad"}).status_code == 400
    assert client.post("/api/admin/events", json={
        "title": "x", "category": "ai", "event_date": "2026-11-01",
        "capacity": -5}).status_code == 400
    assert client.post("/api/admin/events", json={
        "title": "x", "category": "ai", "event_date": "2026-11-01",
        "registration_type": "external"}).status_code == 400


# ---- Scenario 16: students cannot access admin features ------------------
def test_students_blocked_from_admin(client):
    login_and_register_student(client)
    assert client.post("/api/admin/events", json={}).status_code == 403
    assert client.get("/api/admin/events").status_code == 403
    assert client.get("/api/admin/suggestions").status_code == 403
    assert client.post("/api/admin/suggestions/1/approve").status_code == 403


def test_anonymous_blocked(client):
    assert client.get("/api/admin/events").status_code == 401
    assert client.post("/api/events/1/register").status_code == 401


# ---- Scenarios 9-10: registration logic ----------------------------------
def test_internal_registration_rules(client):
    login_admin(client)
    event = create_event(client, capacity=1, registration_deadline="2026-11-19")
    eid = event["id"]
    s2 = app_client2(client, "s2@campus.edu")
    s3 = app_client2(client, "s3@campus.edu")

    assert s2.post(f"/api/events/{eid}/register").status_code == 201
    assert s2.post(f"/api/events/{eid}/register").status_code == 409  # dup
    assert s3.post(f"/api/events/{eid}/register").status_code == 400  # full


app_client2_client_cache = {}


def app_client2(client, email):
    """A second, independent logged-in student session."""
    c2 = client.application.test_client()
    c2.post("/api/auth/register", json={"email": email, "password": "secret1"})
    return c2


def test_registration_deadline_enforced(client):
    login_admin(client)
    event = create_event(client, registration_deadline="2026-01-01")
    login_and_register_student(client)
    res = client.post(f"/api/events/{event['id']}/register")
    assert res.status_code == 400
    assert "closed" in res.get_json()["error"]


def test_external_registration_pending(client):
    login_admin(client)
    event = create_event(client, registration_type="external",
                         registration_url="https://forms.gle/test")
    login_and_register_student(client)
    res = client.post(f"/api/events/{event['id']}/register")
    assert res.status_code == 201
    assert res.get_json()["registration"]["status"] == "pending_external"
    mine = client.get("/api/my-registrations").get_json()["registrations"]
    assert mine[0]["registration"]["status"] == "pending_external"


def test_cancel_registration_frees_seat(client):
    login_admin(client)
    event = create_event(client, capacity=1)
    eid = event["id"]
    s2, s3 = app_client2(client, "s2@campus.edu"), app_client2(client, "s3@campus.edu")
    s2.post(f"/api/events/{eid}/register")
    assert s3.post(f"/api/events/{eid}/register").status_code == 400
    s2.post(f"/api/events/{eid}/cancel-registration")
    assert s3.post(f"/api/events/{eid}/register").status_code == 201


# ---- Scenarios 11-12: suggestions ----------------------------------------
def test_suggestion_flow(client):
    login_and_register_student(client)
    assert client.post("/api/event-suggestions", json={
        "title": "Robotics evening", "category": "coding",
        "description": "bots", "preferredDate": "2026-12-01",
    }).status_code == 201
    mine = client.get("/api/event-suggestions").get_json()["suggestions"]
    assert mine[0]["status"] == "pending"

    # admin reviews
    login_admin(client)
    all_s = client.get("/api/admin/suggestions").get_json()["suggestions"]
    sid = all_s[0]["id"]
    assert client.post(f"/api/admin/suggestions/{sid}/approve").get_json()[
        "suggestion"]["status"] == "approved"
    assert client.post(f"/api/admin/suggestions/{sid}/reject").get_json()[
        "suggestion"]["status"] == "rejected"


def test_suggestion_validation(client):
    login_and_register_student(client)
    assert client.post("/api/event-suggestions", json={
        "title": "x", "category": "coding"}).status_code == 400
    assert client.post("/api/event-suggestions", json={
        "title": "Valid title", "category": "not-a-cat"}).status_code == 400


# ---- Scenarios 13-14: recommendations + AI -------------------------------
def test_recommendations_match_preferences(client):
    login_admin(client)
    create_event(client, category="music", tags="", title="Battle of Bands")
    create_event(client, category="coding", tags="python", title="Hackathon")
    login_and_register_student(client)
    client.put("/api/profile", json={"interests": "coding,a i",
                                     "preferred_categories": "coding"})
    recs = client.get("/api/recommendations").get_json()["recommendations"]
    titles = [e["title"] for e in recs]
    assert "Hackathon" in titles[0]  # boosted first
    assert "Battle of Bands" in titles  # still visible, not hidden


def test_ai_status_and_summary(client):
    login_and_register_student(client)
    login_admin(client)
    event = create_event(client)
    login_student(client)
    status = client.get("/api/ai/status").get_json()
    if status["available"]:
        r = client.post("/api/ai/event-summary", json={"eventId": event["id"]})
        assert r.status_code == 200
        assert len(r.get_json()["summary"]) > 20


def test_app_works_when_ollama_down(client):
    import services.ollama_client as oc
    from app import create_app
    from config import Config as C
    import db as db_mod

    # build an app whose Ollama host is a dead port
    db_mod._migrated.discard(db_mod.DB_PATH)
    class DeadOllama(C):
        OLLAMA_HOST = "http://localhost:9"
    app2 = create_app(DeadOllama)
    c2 = app2.test_client()
    c2.post("/api/auth/register", json={"email": "oll@campus.edu",
                                        "password": "secret1"})
    r = c2.post("/api/ai/assistant", json={"question": "any events?"})
    assert r.status_code == 503
    # core flows unaffected
    assert c2.get("/api/events").status_code == 200
