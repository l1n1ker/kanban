"""User HTTP tests."""
from __future__ import annotations

import sqlite3


def _insert_user(conn: sqlite3.Connection, *, user_id: int, login: str, role: str) -> None:
    conn.execute(
        "INSERT INTO users (id, login, full_name, role, is_active) VALUES (?, ?, ?, ?, ?)",
        (user_id, login, f"{login} name", role, 1),
    )
    conn.commit()


def test_admin_can_create_user(client, db_conn: sqlite3.Connection) -> None:
    _insert_user(db_conn, user_id=1, login="admin", role="admin")

    payload = {
        "login": "user1",
        "full_name": "User One",
        "role": "executor",
        "is_active": True,
    }
    response = client.post(
        "/users",
        json=payload,
        headers={"X-User-Id": "1", "X-User-Role": "admin"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["login"] == "user1"
    assert data["role"] == "executor"


def test_executor_cannot_create_user(client, db_conn: sqlite3.Connection) -> None:
    _insert_user(db_conn, user_id=2, login="exec", role="executor")

    payload = {
        "login": "user2",
        "full_name": "User Two",
        "role": "executor",
        "is_active": True,
    }
    response = client.post(
        "/users",
        json=payload,
        headers={"X-User-Id": "2", "X-User-Role": "executor"},
    )

    assert response.status_code == 403
