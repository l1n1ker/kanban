"""Statuses HTTP tests."""
from __future__ import annotations

import sqlite3


def _insert_user(conn: sqlite3.Connection, *, user_id: int, login: str, role: str) -> None:
    conn.execute(
        "INSERT INTO users (id, login, full_name, role, is_active) VALUES (?, ?, ?, ?, ?)",
        (user_id, login, f"{login} name", role, 1),
    )
    conn.commit()


def test_admin_can_create_and_delete_custom_status(client, db_conn: sqlite3.Connection) -> None:
    _insert_user(db_conn, user_id=1, login="admin", role="admin")

    create_resp = client.post(
        "/statuses",
        json={
            "entity_type": "user",
            "code": "temp_status",
            "name": "Временный",
            "is_active": True,
            "sort_order": 200,
            "is_system": False,
        },
        headers={"X-User-Id": "1", "X-User-Role": "admin"},
    )
    assert create_resp.status_code == 201
    status_id = create_resp.json()["id"]

    delete_resp = client.delete(
        f"/statuses/{status_id}",
        headers={"X-User-Id": "1", "X-User-Role": "admin"},
    )
    assert delete_resp.status_code == 204


def test_cannot_delete_used_status(client, db_conn: sqlite3.Connection) -> None:
    _insert_user(db_conn, user_id=1, login="admin", role="admin")

    create_status = client.post(
        "/statuses",
        json={
            "entity_type": "user",
            "code": "used_status",
            "name": "Заблокирован",
            "is_active": True,
            "sort_order": 210,
            "is_system": False,
        },
        headers={"X-User-Id": "1", "X-User-Role": "admin"},
    )
    sid = create_status.json()["id"]

    create_user = client.post(
        "/users",
        json={
            "login": "u2",
            "full_name": "User 2",
            "role": "executor",
            "is_active": False,
            "status_id": sid,
        },
        headers={"X-User-Id": "1", "X-User-Role": "admin"},
    )
    assert create_user.status_code == 201

    delete_resp = client.delete(
        f"/statuses/{sid}",
        headers={"X-User-Id": "1", "X-User-Role": "admin"},
    )
    assert delete_resp.status_code == 400
