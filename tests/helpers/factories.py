from __future__ import annotations

import sqlite3

from tests.helpers.statuses import status_id


def insert_user(conn: sqlite3.Connection, *, user_id: int, login: str, role: str, is_active: int = 1) -> None:
    sid = status_id(conn, entity_type="user", name="Активен" if is_active == 1 else "Неактивен")
    conn.execute(
        "INSERT INTO users (id, login, full_name, role, is_active, status_id) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, login, f"{login} name", role, is_active, sid),
    )


def insert_pocket(
    conn: sqlite3.Connection,
    *,
    pocket_id: int,
    name: str,
    owner_user_id: int,
    department: str = "IT",
    status_name: str = "Запущен",
) -> None:
    conn.execute(
        "INSERT INTO pockets (id, name, date_start, date_end, status_id, owner_user_id, department) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (pocket_id, name, "2026-02-01", None, status_id(conn, entity_type="pocket", name=status_name), owner_user_id, department),
    )


def insert_project(
    conn: sqlite3.Connection,
    *,
    project_id: int,
    pocket_id: int,
    name: str,
    curator_business_user_id: int,
    curator_it_user_id: int,
    status_name: str = "Активен",
) -> None:
    conn.execute(
        "INSERT INTO projects (id, name, pocket_id, status_id, date_start, date_end, curator_business_user_id, curator_it_user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            project_id,
            name,
            pocket_id,
            status_id(conn, entity_type="project", name=status_name),
            "2026-02-01",
            None,
            curator_business_user_id,
            curator_it_user_id,
        ),
    )
