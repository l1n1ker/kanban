"""RBAC HTTP tests."""
from __future__ import annotations

import sqlite3

from tests.helpers.statuses import status_id as _status_id



def _insert_user(conn: sqlite3.Connection, *, user_id: int, login: str, role: str) -> None:
    conn.execute(
        "INSERT INTO users (id, login, full_name, role, is_active) VALUES (?, ?, ?, ?, ?)",
        (user_id, login, f"{login} name", role, 1),
    )


def _setup_task_context(conn: sqlite3.Connection) -> None:
    _insert_user(conn, user_id=20, login="curator", role="curator")
    _insert_user(conn, user_id=30, login="curator2", role="curator")
    _insert_user(conn, user_id=21, login="executor", role="executor")
    _insert_user(conn, user_id=22, login="owner", role="head")
    conn.execute(
        """
        INSERT INTO pockets (id, name, date_start, date_end, status_id, owner_user_id, department)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (300, "Pocket B", "2026-02-01", None, _status_id(conn, entity_type="pocket", name="Запущен"), 20, "IT"),
    )
    conn.execute(
        """
        INSERT INTO pockets (id, name, date_start, date_end, status_id, owner_user_id, department)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (301, "Pocket C", "2026-02-01", None, _status_id(conn, entity_type="pocket", name="Запущен"), 30, "IT"),
    )
    conn.execute(
        """
        INSERT INTO projects (id, name, pocket_id, status_id, date_start, date_end, curator_business_user_id, curator_it_user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (400, "Project B", 300, _status_id(conn, entity_type="project", name="Активен"), "2026-02-01", None, 20, 20),
    )
    conn.execute(
        """
        INSERT INTO projects (id, name, pocket_id, status_id, date_start, date_end, curator_business_user_id, curator_it_user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (401, "Project C", 301, _status_id(conn, entity_type="project", name="Активен"), "2026-02-01", None, 30, 30),
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


def test_executor_cannot_claim_task(client, db_conn: sqlite3.Connection) -> None:
    _setup_task_context(db_conn)

    create_resp = client.post(
        "/tasks",
        json={
            "project_id": 400,
            "description": "Task RBAC claim",
            "customer": "Business",
            "code_link": None,
        },
        headers={"X-User-Id": "20", "X-User-Role": "curator"},
    )
    task_id = create_resp.json()["id"]
    claim_resp = client.post(
        f"/tasks/{task_id}/claim",
        json={"comment": "try claim"},
        headers={"X-User-Id": "21", "X-User-Role": "executor"},
    )
    assert claim_resp.status_code == 403


def test_curator_can_read_foreign_task_but_cannot_update(client, db_conn: sqlite3.Connection) -> None:
    _setup_task_context(db_conn)
    create_resp = client.post(
        "/tasks",
        json={
            "project_id": 401,
            "description": "Foreign task",
            "customer": "Business",
            "executor_user_id": 21,
            "code_link": None,
        },
        headers={"X-User-Id": "30", "X-User-Role": "curator"},
    )
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    get_resp = client.get(f"/tasks/{task_id}", headers={"X-User-Id": "20", "X-User-Role": "curator"})
    patch_resp = client.patch(
        f"/tasks/{task_id}",
        json={"description": "hack"},
        headers={"X-User-Id": "20", "X-User-Role": "curator"},
    )

    assert get_resp.status_code == 200
    assert patch_resp.status_code == 403


def test_curator_list_tasks_reads_full_picture(client, db_conn: sqlite3.Connection) -> None:
    _setup_task_context(db_conn)
    own = client.post(
        "/tasks",
        json={
            "project_id": 400,
            "description": "Own task",
            "customer": "Business",
            "executor_user_id": 21,
            "code_link": None,
        },
        headers={"X-User-Id": "20", "X-User-Role": "curator"},
    )
    foreign = client.post(
        "/tasks",
        json={
            "project_id": 401,
            "description": "Foreign task",
            "customer": "Business",
            "executor_user_id": 21,
            "code_link": None,
        },
        headers={"X-User-Id": "30", "X-User-Role": "curator"},
    )
    assert own.status_code == 201
    assert foreign.status_code == 201

    list_resp = client.get("/tasks", headers={"X-User-Id": "20", "X-User-Role": "curator"})
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert {item["project_id"] for item in body} == {400, 401}
