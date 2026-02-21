"""Task HTTP tests."""
from __future__ import annotations

import sqlite3

from tests.helpers.statuses import status_id as _status_id



def _insert_user(conn: sqlite3.Connection, *, user_id: int, login: str, role: str) -> None:
    conn.execute(
        "INSERT INTO users (id, login, full_name, role, is_active) VALUES (?, ?, ?, ?, ?)",
        (user_id, login, f"{login} name", role, 1),
    )


def _insert_pocket(conn: sqlite3.Connection, *, pocket_id: int, owner_user_id: int) -> None:
    conn.execute(
        """
        INSERT INTO pockets (id, name, date_start, date_end, status_id, owner_user_id, department)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            pocket_id,
            "Pocket A",
            "2026-02-01",
            None,
            _status_id(conn, entity_type="pocket", name="Запущен"),
            owner_user_id,
            "IT",
        ),
    )


def _insert_project(conn: sqlite3.Connection, *, project_id: int, pocket_id: int, curator_user_id: int) -> None:
    conn.execute(
        """
        INSERT INTO projects (id, name, pocket_id, status_id, date_start, date_end, curator_business_user_id, curator_it_user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project_id,
            "Project A",
            pocket_id,
            _status_id(conn, entity_type="project", name="Активен"),
            "2026-02-01",
            None,
            curator_user_id,
            curator_user_id,
        ),
    )


def _setup_task_context(conn: sqlite3.Connection) -> None:
    _insert_user(conn, user_id=10, login="curator", role="curator")
    _insert_user(conn, user_id=11, login="executor", role="executor")
    _insert_user(conn, user_id=12, login="owner", role="head")
    _insert_pocket(conn, pocket_id=100, owner_user_id=10)
    _insert_project(conn, project_id=200, pocket_id=100, curator_user_id=10)
    conn.commit()


def test_curator_can_create_task(client, db_conn: sqlite3.Connection) -> None:
    _setup_task_context(db_conn)

    payload = {
        "project_id": 200,
        "description": "Task A",
        "customer": "Business",
        "executor_user_id": 11,
        "code_link": None,
    }
    response = client.post(
        "/tasks",
        json=payload,
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "Создана"
    assert data["project_id"] == 200


def test_curator_can_create_unassigned_task(client, db_conn: sqlite3.Connection) -> None:
    _setup_task_context(db_conn)

    payload = {
        "project_id": 200,
        "description": "Task without executor",
        "customer": "Business",
        "code_link": None,
    }
    response = client.post(
        "/tasks",
        json=payload,
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["executor_user_id"] is None


def test_start_unassigned_task_returns_conflict(client, db_conn: sqlite3.Connection) -> None:
    _setup_task_context(db_conn)
    create_resp = client.post(
        "/tasks",
        json={"project_id": 200, "description": "Queue task", "customer": "Business", "code_link": None},
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )
    created_status = create_resp.json()["status"]
    task_id = create_resp.json()["id"]
    start_resp = client.post(
        f"/tasks/{task_id}/start",
        json={"comment": "start"},
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )
    assert start_resp.status_code == 409


def test_curator_can_assign_task_without_start(client, db_conn: sqlite3.Connection) -> None:
    _setup_task_context(db_conn)
    create_resp = client.post(
        "/tasks",
        json={"project_id": 200, "description": "Queue task", "customer": "Business", "code_link": None},
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )
    created_status = create_resp.json()["status"]
    task_id = create_resp.json()["id"]
    assign_resp = client.post(
        f"/tasks/{task_id}/assign",
        json={"executor_user_id": 11, "comment": "assign"},
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )
    assert assign_resp.status_code == 200
    body = assign_resp.json()
    assert body["executor_user_id"] == 11
    assert body["status"] == created_status
    assert body["date_start_work"] is None

def test_task_status_transition_flow(client, db_conn: sqlite3.Connection) -> None:
    _setup_task_context(db_conn)

    create_payload = {
        "project_id": 200,
        "description": "Task B",
        "customer": "Business",
        "executor_user_id": 11,
        "code_link": None,
    }
    create_resp = client.post(
        "/tasks",
        json=create_payload,
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )
    task_id = create_resp.json()["id"]

    start_resp = client.post(
        f"/tasks/{task_id}/start",
        json={"comment": "start"},
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] == "В работе"

    pause_resp = client.post(
        f"/tasks/{task_id}/pause",
        json={"comment": "pause"},
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )
    assert pause_resp.status_code == 200
    assert pause_resp.json()["status"] == "Приостановлена"

    resume_resp = client.post(
        f"/tasks/{task_id}/resume",
        json={"comment": "resume"},
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )
    assert resume_resp.status_code == 200
    assert resume_resp.json()["status"] == "В работе"

    complete_resp = client.post(
        f"/tasks/{task_id}/complete",
        json={"comment": "done"},
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == "Завершена"


def test_curator_can_claim_unassigned_task(client, db_conn: sqlite3.Connection) -> None:
    _setup_task_context(db_conn)
    create_payload = {
        "project_id": 200,
        "description": "Queue task",
        "customer": "Business",
        "code_link": None,
    }
    create_resp = client.post(
        "/tasks",
        json=create_payload,
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    claim_resp = client.post(
        f"/tasks/{task_id}/claim",
        json={"comment": "take"},
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )
    assert claim_resp.status_code == 200
    body = claim_resp.json()
    assert body["executor_user_id"] == 10
    assert body["status"] == "В работе"
    assert body["date_start_work"] is not None


def test_executor_cannot_claim_task(client, db_conn: sqlite3.Connection) -> None:
    _setup_task_context(db_conn)
    create_resp = client.post(
        "/tasks",
        json={"project_id": 200, "description": "Queue task", "customer": "Business", "code_link": None},
        headers={"X-User-Id": "10", "X-User-Role": "curator"},
    )
    task_id = create_resp.json()["id"]
    claim = client.post(
        f"/tasks/{task_id}/claim",
        json={"comment": "take"},
        headers={"X-User-Id": "11", "X-User-Role": "executor"},
    )
    assert claim.status_code == 403
