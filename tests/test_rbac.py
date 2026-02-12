"""RBAC HTTP tests."""
from __future__ import annotations

import sqlite3


def _insert_user(conn: sqlite3.Connection, *, user_id: int, login: str, role: str) -> None:
    conn.execute(
        "INSERT INTO users (id, login, full_name, role, is_active) VALUES (?, ?, ?, ?, ?)",
        (user_id, login, f"{login} name", role, 1),
    )


def _setup_task_context(conn: sqlite3.Connection) -> None:
    _insert_user(conn, user_id=20, login="curator", role="curator")
    _insert_user(conn, user_id=21, login="executor", role="executor")
    _insert_user(conn, user_id=22, login="owner", role="head")
    conn.execute(
        """
        INSERT INTO pockets (id, name, date_start, date_end, status, owner_user_id, department)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (300, "Pocket B", "2026-02-01", None, "Запущен", 22, "IT"),
    )
    conn.execute(
        """
        INSERT INTO projects (id, name, pocket_id, status, date_start, date_end, curator_business_user_id, curator_it_user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (400, "Project B", 300, "Активен", "2026-02-01", None, 20, 20),
    )
    conn.commit()


def test_executor_cannot_change_task_status(client, db_conn: sqlite3.Connection) -> None:
    _setup_task_context(db_conn)

    create_resp = client.post(
        "/tasks",
        json={
            "project_id": 400,
            "description": "Task RBAC",
            "customer": "Business",
            "executor_user_id": 21,
            "code_link": None,
        },
        headers={"X-User-Id": "20", "X-User-Role": "curator"},
    )
    task_id = create_resp.json()["id"]

    start_resp = client.post(
        f"/tasks/{task_id}/start",
        json={"comment": "try start"},
        headers={"X-User-Id": "21", "X-User-Role": "executor"},
    )

    assert start_resp.status_code == 403
