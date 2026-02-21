"""RBAC matrix tests for assign/update in own vs foreign pocket."""
from __future__ import annotations

import sqlite3


def _insert_user(conn: sqlite3.Connection, *, user_id: int, login: str, role: str) -> None:
    conn.execute(
        "INSERT INTO users (id, login, full_name, role, is_active) VALUES (?, ?, ?, ?, ?)",
        (user_id, login, f"{login} name", role, 1),
    )


def _setup_context(conn: sqlite3.Connection) -> None:
    _insert_user(conn, user_id=2, login="head", role="head")
    _insert_user(conn, user_id=10, login="cur1", role="curator")
    _insert_user(conn, user_id=20, login="cur2", role="curator")
    _insert_user(conn, user_id=30, login="exec", role="executor")
    conn.execute(
        """
        INSERT INTO pockets (id, name, date_start, date_end, status, owner_user_id, department)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (101, "P1", "2026-02-01", None, "Запущен", 10, "IT"),
    )
    conn.execute(
        """
        INSERT INTO pockets (id, name, date_start, date_end, status, owner_user_id, department)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (102, "P2", "2026-02-01", None, "Запущен", 20, "IT"),
    )
    conn.execute(
        """
        INSERT INTO projects (id, name, pocket_id, status, date_start, date_end, curator_business_user_id, curator_it_user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (201, "PR1", 101, "Активен", "2026-02-01", None, 10, 10),
    )
    conn.execute(
        """
        INSERT INTO projects (id, name, pocket_id, status, date_start, date_end, curator_business_user_id, curator_it_user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (202, "PR2", 102, "Активен", "2026-02-01", None, 20, 20),
    )
    conn.commit()


def _create_task(client, *, project_id: int, actor_id: int, actor_role: str) -> int:
    resp = client.post(
        "/tasks",
        json={"project_id": project_id, "description": "task", "customer": "biz", "code_link": None},
        headers={"X-User-Id": str(actor_id), "X-User-Role": actor_role},
    )
    assert resp.status_code == 201
    return int(resp.json()["id"])


def test_curator_assign_own_vs_foreign(client, db_conn: sqlite3.Connection) -> None:
    _setup_context(db_conn)
    own_task = _create_task(client, project_id=201, actor_id=10, actor_role="curator")
    foreign_task = _create_task(client, project_id=202, actor_id=20, actor_role="curator")

    own_assign = client.post(
        f"/tasks/{own_task}/assign",
        json={"executor_user_id": 30},
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )
    foreign_assign = client.post(
        f"/tasks/{foreign_task}/assign",
        json={"executor_user_id": 30},
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )

    assert own_assign.status_code == 200
    assert foreign_assign.status_code == 403


def test_executor_cannot_assign(client, db_conn: sqlite3.Connection) -> None:
    _setup_context(db_conn)
    task_id = _create_task(client, project_id=201, actor_id=10, actor_role="curator")
    resp = client.post(
        f"/tasks/{task_id}/assign",
        json={"executor_user_id": 30},
        headers={"X-User-Id": "30", "X-User-Role": "executor"},
    )
    assert resp.status_code == 403


def test_head_can_assign_any(client, db_conn: sqlite3.Connection) -> None:
    _setup_context(db_conn)
    task_id = _create_task(client, project_id=202, actor_id=20, actor_role="curator")
    resp = client.post(
        f"/tasks/{task_id}/assign",
        json={"executor_user_id": 30},
        headers={"X-User-Id": "2", "X-User-Role": "head"},
    )
    assert resp.status_code == 200
