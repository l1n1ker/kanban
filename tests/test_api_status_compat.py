"""Backward compatibility tests for temporary `status` API field."""
from __future__ import annotations

import sqlite3


def _insert_user(conn: sqlite3.Connection, *, user_id: int, login: str, role: str) -> None:
    conn.execute(
        "INSERT INTO users (id, login, full_name, role, is_active, status_id) VALUES (?, ?, ?, ?, ?, ?)",
        (
            user_id,
            login,
            f"{login} name",
            role,
            1,
            conn.execute(
                "SELECT id FROM statuses WHERE entity_type = 'user' AND name = 'Активен' LIMIT 1"
            ).fetchone()["id"],
        ),
    )


def _status_id(conn: sqlite3.Connection, *, entity_type: str, name: str) -> int:
    row = conn.execute(
        "SELECT id FROM statuses WHERE entity_type = ? AND name = ? LIMIT 1",
        (entity_type, name),
    ).fetchone()
    assert row is not None
    return int(row["id"])


def test_create_pocket_accepts_compat_status_input(client, db_conn: sqlite3.Connection) -> None:
    _insert_user(db_conn, user_id=1, login="head1", role="head")
    db_conn.commit()

    resp = client.post(
        "/pockets",
        json={
            "name": "Compat Pocket",
            "date_start": "2026-02-01",
            "date_end": None,
            "status": "Запущен",
            "owner_user_id": 1,
            "department": "IT",
        },
        headers={"X-User-Id": "1", "X-User-Role": "head"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "Запущен"
    assert int(body["status_id"]) == _status_id(db_conn, entity_type="pocket", name="Запущен")


def test_create_project_accepts_compat_status_input(client, db_conn: sqlite3.Connection) -> None:
    _insert_user(db_conn, user_id=2, login="head2", role="head")
    db_conn.commit()

    pocket_resp = client.post(
        "/pockets",
        json={
            "name": "Base",
            "date_start": "2026-02-01",
            "date_end": None,
            "status_id": _status_id(db_conn, entity_type="pocket", name="Запущен"),
            "owner_user_id": 2,
            "department": "IT",
        },
        headers={"X-User-Id": "2", "X-User-Role": "head"},
    )
    assert pocket_resp.status_code == 201
    pocket_id = int(pocket_resp.json()["id"])

    project_resp = client.post(
        "/projects",
        json={
            "name": "Compat Project",
            "project_code": "CP-1",
            "pocket_id": pocket_id,
            "status": "Активен",
            "date_start": "2026-02-01",
            "date_end": None,
            "curator_business_user_id": 2,
            "curator_it_user_id": 2,
        },
        headers={"X-User-Id": "2", "X-User-Role": "head"},
    )
    assert project_resp.status_code == 201
    body = project_resp.json()
    assert body["status"] == "Активен"
    assert int(body["status_id"]) == _status_id(db_conn, entity_type="project", name="Активен")


def test_create_pocket_returns_derived_status_for_status_id_input(client, db_conn: sqlite3.Connection) -> None:
    _insert_user(db_conn, user_id=3, login="head3", role="head")
    db_conn.commit()

    resp = client.post(
        "/pockets",
        json={
            "name": "Canonical Pocket",
            "date_start": "2026-02-01",
            "date_end": None,
            "status_id": _status_id(db_conn, entity_type="pocket", name="Запущен"),
            "owner_user_id": 3,
            "department": "IT",
        },
        headers={"X-User-Id": "3", "X-User-Role": "head"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "Запущен"
    assert int(body["status_id"]) == _status_id(db_conn, entity_type="pocket", name="Запущен")


def test_list_projects_compat_status_filter_maps_to_status_id(client, db_conn: sqlite3.Connection) -> None:
    _insert_user(db_conn, user_id=4, login="head4", role="head")
    db_conn.commit()

    pocket_resp = client.post(
        "/pockets",
        json={
            "name": "Compat Filter Base",
            "date_start": "2026-02-01",
            "date_end": None,
            "status_id": _status_id(db_conn, entity_type="pocket", name="Запущен"),
            "owner_user_id": 4,
            "department": "IT",
        },
        headers={"X-User-Id": "4", "X-User-Role": "head"},
    )
    assert pocket_resp.status_code == 201
    pocket_id = int(pocket_resp.json()["id"])

    active_resp = client.post(
        "/projects",
        json={
            "name": "Active Project",
            "project_code": "CF-A",
            "pocket_id": pocket_id,
            "status_id": _status_id(db_conn, entity_type="project", name="Активен"),
            "date_start": "2026-02-01",
            "date_end": None,
            "curator_business_user_id": 4,
            "curator_it_user_id": 4,
        },
        headers={"X-User-Id": "4", "X-User-Role": "head"},
    )
    assert active_resp.status_code == 201

    done_resp = client.post(
        "/projects",
        json={
            "name": "Done Project",
            "project_code": "CF-D",
            "pocket_id": pocket_id,
            "status_id": _status_id(db_conn, entity_type="project", name="Завершён"),
            "date_start": "2026-02-01",
            "date_end": None,
            "curator_business_user_id": 4,
            "curator_it_user_id": 4,
        },
        headers={"X-User-Id": "4", "X-User-Role": "head"},
    )
    assert done_resp.status_code == 201

    filtered = client.get(
        "/projects",
        params={"pocket_id": pocket_id, "status": "Активен"},
        headers={"X-User-Id": "4", "X-User-Role": "head"},
    )
    assert filtered.status_code == 200
    rows = filtered.json()
    assert len(rows) == 1
    assert rows[0]["name"] == "Active Project"
    assert rows[0]["status"] == "Активен"
