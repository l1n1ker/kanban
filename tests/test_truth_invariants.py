"""Truth-model invariants for statuses, lifecycle and action log."""
from __future__ import annotations

import sqlite3

from tests.helpers.statuses import status_id as _status_id


def _insert_user(conn: sqlite3.Connection, *, user_id: int, login: str, role: str) -> None:
    conn.execute(
        "INSERT INTO users (id, login, full_name, role, is_active) VALUES (?, ?, ?, ?, ?)",
        (user_id, login, f"{login} name", role, 1),
    )


def _setup_context(conn: sqlite3.Connection) -> None:
    _insert_user(conn, user_id=10, login="curator", role="curator")
    _insert_user(conn, user_id=11, login="executor", role="executor")
    conn.execute(
        """
        INSERT INTO pockets (id, name, date_start, date_end, status_id, owner_user_id, department)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (100, "Pocket A", "2026-02-01", None, _status_id(conn, entity_type="pocket", name="Запущен"), 10, "IT"),
    )
    conn.execute(
        """
        INSERT INTO projects (id, name, pocket_id, status_id, date_start, date_end, curator_business_user_id, curator_it_user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (200, "Project A", 100, _status_id(conn, entity_type="project", name="Активен"), "2026-02-01", None, 10, 10),
    )
    conn.commit()


def test_task_status_and_status_id_are_consistent_on_transition(client, db_conn: sqlite3.Connection) -> None:
    _setup_context(db_conn)
    create = client.post(
        "/tasks",
        json={
            "project_id": 200,
            "description": "Invariant task",
            "customer": "biz",
            "executor_user_id": 11,
            "code_link": None,
        },
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )
    assert create.status_code == 201
    task_id = int(create.json()["id"])

    start = client.post(
        f"/tasks/{task_id}/start",
        json={"comment": "start"},
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )
    assert start.status_code == 200
    body = start.json()
    assert body["status"] == "В работе"
    assert int(body["status_id"]) == _status_id(db_conn, entity_type="task", name="В работе")


def test_claim_logs_assign_and_update_status_actions(client, db_conn: sqlite3.Connection) -> None:
    _setup_context(db_conn)
    create = client.post(
        "/tasks",
        json={"project_id": 200, "description": "Queue", "customer": "biz", "code_link": None},
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )
    assert create.status_code == 201
    task_id = int(create.json()["id"])

    claim = client.post(
        f"/tasks/{task_id}/claim",
        json={"comment": "claim"},
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )
    assert claim.status_code == 200

    logs = client.get(
        "/action_log",
        params={"entity_type": "task", "entity_id": task_id},
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )
    assert logs.status_code == 200
    actions = [row["action_type"] for row in logs.json()]
    assert "assign" in actions
    assert "update_status" in actions
