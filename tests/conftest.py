"""Shared fixtures for backend tests."""
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app  # noqa: E402
from config import Config  # noqa: E402


class TestConfig(Config):
    DEBUG = False
    TESTING = True
    DB_BACKEND = "memory"


@pytest.fixture()
def app():
    return create_app(TestConfig)


@pytest.fixture()
def client(app):
    return app.test_client()


def make_admin(client, uid="admin1"):
    res = client.post("/api/auth/demo-login", json={"uid": uid, "isAdmin": True})
    return res.get_json()["token"]


def make_student(client, uid="s1", interests=None):
    res = client.post("/api/auth/demo-login",
                      json={"uid": uid, "name": "Student", "year": "2",
                            "department": "CSE"})
    token = res.get_json()["token"]
    if interests:
        client.put("/api/profile/interests",
                   headers={"Authorization": f"Bearer {token}"},
                   json={"interests": interests})
    return token


def create_event(client, admin_token, event_id="e-test", **overrides):
    payload = {
        "title": "Test Event", "category": "coding", "date": "2026-10-20",
        "startTime": "10:00", "endTime": "16:00", "capacity": 50,
        "tags": ["python"], "status": "published",
        "registrationDeadline": "2026-10-19",
    }
    payload.update(overrides)
    res = client.post("/api/admin/events",
                      headers={"Authorization": f"Bearer {admin_token}"},
                      json=payload)
    assert res.status_code == 201
    return res.get_json()["event"]
