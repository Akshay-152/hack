"""Shared fixtures: Flask test client on a fresh SQLite DB per test."""
import os
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

_tmpdir = tempfile.mkdtemp(prefix="campus_test_")
os.environ["DB_PATH"] = os.path.join(_tmpdir, "test.db")
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "admin"

import db  # noqa: E402
db.DB_PATH = os.path.join(_tmpdir, "test.db")

from app import create_app  # noqa: E402
from config import Config  # noqa: E402


class TestConfig(Config):
    DEBUG = False
    TESTING = True
    DB_BACKEND = "memory"  # unused now, kept for config compatibility


@pytest.fixture()
def app():
    # fresh DB per test for isolation
    db._migrated.discard(db.DB_PATH)
    for table in ("event_suggestions", "event_registrations", "events",
                  "student_profiles", "users"):
        db.execute(f"DROP TABLE IF EXISTS {table}")
    db.init_db()
    from auth_service import seed_admin
    seed_admin()
    return create_app(TestConfig)


@pytest.fixture()
def client(app):
    return app.test_client()


# ---- convenience helpers -------------------------------------------------
def login_admin(client, username="admin", password="admin"):
    res = client.post("/api/auth/login",
                      json={"email": username, "password": password})
    assert res.status_code == 200
    return res.get_json()["user"]


def register_student(client, email="s1@campus.edu", password="secret1"):
    res = client.post("/api/auth/register",
                      json={"email": email, "password": password})
    return res.get_json()["user"]


def login_student(client, email="s1@campus.edu", password="secret1"):
    res = client.post("/api/auth/login",
                      json={"email": email, "password": password})
    assert res.status_code == 200
    return res.get_json()["user"]


def create_event(client, **overrides):
    payload = {
        "title": "Test Event", "category": "coding", "event_date": "2026-11-20",
        "start_time": "10:00", "end_time": "16:00", "capacity": 50,
        "tags": "python", "status": "published",
        "registration_deadline": "2026-11-19",
    }
    payload.update(overrides)
    res = client.post("/api/admin/events", json=payload)
    assert res.status_code == 201, res.get_json()
    return res.get_json()["event"]
