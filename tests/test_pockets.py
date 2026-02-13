"""Pocket HTTP tests."""
from __future__ import annotations

import sqlite3


def _insert_user(conn: sqlite3.Connection, *, user_id: int, login: str, role: str) -> None:
    conn.execute(
        "INSERT INTO users (id, login, full_name, role, is_active) VALUES (?, ?, ?, ?, ?)",
        (user_id, login, f"{login} name", role, 1),
    )


def _insert_pocket(conn: sqlite3.Connection, *, pocket_id: int, owner_user_id: int) -> None:
    conn.execute(
        """
        INSERT INTO pockets (id, name, date_start, date_end, status, owner_user_id, department)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (pocket_id, "Pocket X", "2026-02-01", None, "Запущен", owner_user_id, "IT"),
    )


def test_head_can_archive_pocket(client, db_conn: sqlite3.Connection) -> None:
    _insert_user(db_conn, user_id=31, login="head1", role="head")
    _insert_pocket(db_conn, pocket_id=700, owner_user_id=31)
    db_conn.commit()

    response = client.patch(
        "/pockets/700",
        json={"status": "Завершён"},
        headers={"X-User-Id": "31", "X-User-Role": "head"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Завершён"


def test_executor_cannot_create_or_update_pocket(client, db_conn: sqlite3.Connection) -> None:
    _insert_user(db_conn, user_id=32, login="exec1", role="executor")
    _insert_user(db_conn, user_id=33, login="head2", role="head")
    _insert_pocket(db_conn, pocket_id=701, owner_user_id=33)
    db_conn.commit()

    create_resp = client.post(
        "/pockets",
        json={
            "name": "New Pocket",
            "date_start": "2026-02-01",
            "date_end": None,
            "status": "Запущен",
            "owner_user_id": 33,
            "department": "IT",
        },
        headers={"X-User-Id": "32", "X-User-Role": "executor"},
    )
    assert create_resp.status_code == 403

    update_resp = client.patch(
        "/pockets/701",
        json={"name": "Renamed"},
        headers={"X-User-Id": "32", "X-User-Role": "executor"},
    )
    assert update_resp.status_code == 403


def test_pocket_date_validation(client, db_conn: sqlite3.Connection) -> None:
    _insert_user(db_conn, user_id=34, login="head3", role="head")
    db_conn.commit()

    response = client.post(
        "/pockets",
        json={
            "name": "Bad Dates",
            "date_start": "2026-03-10",
            "date_end": "2026-03-01",
            "status": "Запущен",
            "owner_user_id": 34,
            "department": "IT",
        },
        headers={"X-User-Id": "34", "X-User-Role": "head"},
    )

    assert response.status_code == 400
    assert "date_end cannot be earlier than date_start" in response.text
