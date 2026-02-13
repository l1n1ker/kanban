"""Pytest fixtures for FastAPI HTTP layer tests."""
from __future__ import annotations

import sqlite3
from typing import Iterator

import pytest
from fastapi import Header
from fastapi.testclient import TestClient

from backend.http.app import create_app
from backend.http.common import get_services
from backend.services import Services


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    status_id INTEGER
);

CREATE TABLE IF NOT EXISTS pockets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    date_start TEXT NOT NULL,
    date_end TEXT,
    status TEXT NOT NULL,
    status_id INTEGER,
    owner_user_id INTEGER NOT NULL,
    department TEXT NOT NULL,
    FOREIGN KEY(owner_user_id) REFERENCES users(id),
    FOREIGN KEY(status) REFERENCES pocket_statuses(name)
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    project_code TEXT,
    pocket_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    status_id INTEGER,
    date_start TEXT NOT NULL,
    date_end TEXT,
    curator_business_user_id INTEGER NOT NULL,
    curator_it_user_id INTEGER NOT NULL,
    FOREIGN KEY(pocket_id) REFERENCES pockets(id),
    FOREIGN KEY(curator_business_user_id) REFERENCES users(id),
    FOREIGN KEY(curator_it_user_id) REFERENCES users(id),
    FOREIGN KEY(status) REFERENCES project_statuses(name)
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL,
    project_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    status_id INTEGER,
    date_created TEXT NOT NULL,
    date_start_work TEXT,
    date_done TEXT,
    executor_user_id INTEGER,
    customer TEXT,
    code_link TEXT,
    FOREIGN KEY(project_id) REFERENCES projects(id),
    FOREIGN KEY(executor_user_id) REFERENCES users(id),
    FOREIGN KEY(status) REFERENCES task_statuses(name)
);

CREATE TABLE IF NOT EXISTS task_pauses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    date_start TEXT NOT NULL,
    date_end TEXT,
    FOREIGN KEY(task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS action_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    action_type TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    comment TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS pocket_statuses (
    name TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS project_statuses (
    name TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS task_statuses (
    name TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS statuses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 100,
    is_system INTEGER NOT NULL DEFAULT 0
);
"""


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_SQL)
    conn.executemany(
        "INSERT OR IGNORE INTO pocket_statuses(name) VALUES (?)",
        [("Запущен",), ("Завершён",)],
    )
    conn.executemany(
        "INSERT OR IGNORE INTO project_statuses(name) VALUES (?)",
        [("Активен",), ("Завершён",)],
    )
    conn.executemany(
        "INSERT OR IGNORE INTO task_statuses(name) VALUES (?)",
        [("Создана",), ("В работе",), ("Приостановлена",), ("Завершена",)],
    )
    conn.executemany(
        "INSERT OR IGNORE INTO statuses(entity_type, code, name, is_active, sort_order, is_system) VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("pocket", "running", "Запущен", 1, 10, 1),
            ("pocket", "done", "Завершён", 1, 20, 1),
            ("project", "active", "Активен", 1, 10, 1),
            ("project", "done", "Завершён", 1, 20, 1),
            ("task", "created", "Создана", 1, 10, 1),
            ("task", "in_progress", "В работе", 1, 20, 1),
            ("task", "paused", "Приостановлена", 1, 30, 1),
            ("task", "done", "Завершена", 1, 40, 1),
            ("user", "active", "Активен", 1, 10, 1),
            ("user", "inactive", "Неактивен", 1, 20, 1),
        ],
    )
    conn.commit()


@pytest.fixture()
def db_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    _init_schema(conn)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture()
def client(db_conn: sqlite3.Connection) -> Iterator[TestClient]:
    app = create_app()
    app.router.on_startup.clear()

    def override_get_services(
        x_user_id: int = Header(..., alias="X-User-Id"),
        x_user_role: str = Header(..., alias="X-User-Role"),
    ) -> Iterator[Services]:
        actor_user = {"id": x_user_id, "role": x_user_role}
        svc = Services(db_conn, actor_user=actor_user)
        try:
            yield svc
            db_conn.commit()
        finally:
            pass

    app.dependency_overrides[get_services] = override_get_services
    with TestClient(app) as test_client:
        yield test_client
