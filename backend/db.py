"""SQLite database layer (spec section 9 schema).

Tables: users, student_profiles, events, event_registrations,
event_suggestions. Foreign keys ON, parameterized queries everywhere,
auto-init/migrate at startup.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime

DB_PATH = os.getenv("DB_PATH",
                    os.path.join(os.path.dirname(__file__), "campus_events.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'student' CHECK (role IN ('student','admin')),
    created_at    TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email);

CREATE TABLE IF NOT EXISTS student_profiles (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id              INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    full_name            TEXT DEFAULT '',
    college_id           TEXT DEFAULT '',
    course               TEXT DEFAULT '',
    department           TEXT DEFAULT '',
    semester             TEXT DEFAULT '',
    interests            TEXT DEFAULT '',
    preferred_categories TEXT DEFAULT '',
    profile_photo        TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS events (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    title                 TEXT NOT NULL,
    description           TEXT DEFAULT '',
    category              TEXT NOT NULL,
    poster_path           TEXT DEFAULT '',
    event_date            TEXT NOT NULL,
    start_time            TEXT DEFAULT '',
    end_time              TEXT DEFAULT '',
    venue                 TEXT DEFAULT '',
    organizer             TEXT DEFAULT '',
    registration_deadline TEXT DEFAULT '',
    capacity              INTEGER NOT NULL DEFAULT 0,
    registration_type     TEXT NOT NULL DEFAULT 'internal'
                          CHECK (registration_type IN ('internal','external','both')),
    registration_url      TEXT DEFAULT '',
    registration_instructions TEXT DEFAULT '',
    tags                  TEXT DEFAULT '',
    status                TEXT NOT NULL DEFAULT 'draft'
                          CHECK (status IN ('draft','published','cancelled')),
    created_by            INTEGER REFERENCES users(id),
    created_at            TEXT NOT NULL,
    updated_at            TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_status_date ON events(status, event_date);

CREATE TABLE IF NOT EXISTS event_registrations (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id           INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    student_user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    registration_status TEXT NOT NULL DEFAULT 'registered'
                       CHECK (registration_status IN
                             ('registered','pending_external','cancelled')),
    registered_at      TEXT NOT NULL,
    UNIQUE (event_id, student_user_id)
);
CREATE INDEX IF NOT EXISTS idx_reg_student ON event_registrations(student_user_id);

CREATE TABLE IF NOT EXISTS event_suggestions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    student_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title          TEXT NOT NULL,
    category       TEXT NOT NULL,
    description    TEXT DEFAULT '',
    preferred_date TEXT DEFAULT '',
    reason         TEXT DEFAULT '',
    status         TEXT NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending','approved','rejected')),
    created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sugg_student ON event_suggestions(student_user_id);
"""

_migrated: set[str] = set()


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def query(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    with get_db() as conn:
        return conn.execute(sql, params).fetchall()


def query_one(sql: str, params: tuple = ()) -> sqlite3.Row | None:
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: tuple = ()) -> int:
    with get_db() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def init_db() -> None:
    """Create tables if missing; add any missing columns (light migration)."""
    if DB_PATH in _migrated:
        return
    with get_db() as conn:
        conn.executescript(SCHEMA)
        # light migration: add columns introduced after first schema
        cols = {r["name"] for r in
                conn.execute("PRAGMA table_info(events)").fetchall()}
        for name, ddl in [
            ("registration_instructions", "TEXT DEFAULT ''"),
            ("registration_type", "TEXT NOT NULL DEFAULT 'internal'"),
        ]:
            if name not in cols:
                conn.execute(f"ALTER TABLE events ADD COLUMN {name} {ddl}")
        conn.commit()
    _migrated.add(DB_PATH)
