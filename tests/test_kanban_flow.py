"""Kanban flow API tests for queue/created semantics."""
from __future__ import annotations

import sqlite3


def _insert_user(conn: sqlite3.Connection, *, user_id: int, login: str, role: str) -> None:
    conn.execute(
        "INSERT INTO users (id, login, full_name, role, is_active) VALUES (?, ?, ?, ?, ?)",
        (user_id, login, f"{login} name", role, 1),
    )


def _setup_context(conn: sqlite3.Connection) -> None:
    _insert_user(conn, user_id=1, login="admin", role="admin")
    _insert_user(conn, user_id=10, login="cur1", role="curator")
    _insert_user(conn, user_id=11, login="exec1", role="executor")
    conn.execute(
        """
        INSERT INTO pockets (id, name, date_start, date_end, status, owner_user_id, department)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (100, "Pocket A", "2026-02-01", None, "Запущен", 10, "IT"),
    )
    conn.execute(
        """
        INSERT INTO projects (id, name, pocket_id, status, date_start, date_end, curator_business_user_id, curator_it_user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (200, "Project A", 100, "Активен", "2026-02-01", None, 10, 10),
    )
    conn.commit()


def test_assign_keeps_status_created(client, db_conn: sqlite3.Connection) -> None:
    _setup_context(db_conn)
    create = client.post(
        "/tasks",
        json={"project_id": 200, "description": "queue", "customer": "biz", "code_link": None},
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )
    assert create.status_code == 201
    task_id = create.json()["id"]

    assign = client.post(
        f"/tasks/{task_id}/assign",
        json={"executor_user_id": 11, "comment": "assign only"},
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )
    assert assign.status_code == 200
    body = assign.json()
    assert body["executor_user_id"] == 11
    assert body["status"] == "Создана"
    assert body["date_start_work"] is None


def test_start_requires_executor(client, db_conn: sqlite3.Connection) -> None:
    _setup_context(db_conn)
    create = client.post(
        "/tasks",
        json={"project_id": 200, "description": "queue", "customer": "biz", "code_link": None},
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )
    assert create.status_code == 201
    task_id = create.json()["id"]

    start = client.post(
        f"/tasks/{task_id}/start",
        json={"comment": "start w/o executor"},
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )
    assert start.status_code == 409


def test_claim_assigns_and_starts(client, db_conn: sqlite3.Connection) -> None:
    _setup_context(db_conn)
    create = client.post(
        "/tasks",
        json={"project_id": 200, "description": "queue", "customer": "biz", "code_link": None},
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )
    task_id = create.json()["id"]
    claim = client.post(
        f"/tasks/{task_id}/claim",
        json={"comment": "take"},
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )
    assert claim.status_code == 200
    body = claim.json()
    assert body["executor_user_id"] == 10
    assert body["status"] == "В работе"
    assert body["date_start_work"] is not None
