"""Database validators."""
from __future__ import annotations

import sqlite3

from .migrations import table_has_column


def validate_status_consistency(conn: sqlite3.Connection) -> None:
    for table_name, entity_type in (("pockets", "pocket"), ("projects", "project"), ("tasks", "task")):
        if not table_has_column(conn, table_name, "status"):
            continue
        rows = conn.execute(
            f"""
            SELECT t.id
            FROM {table_name} t
            JOIN statuses s ON s.id = t.status_id
            WHERE t.status IS NOT NULL
              AND t.status_id IS NOT NULL
              AND s.entity_type = ?
              AND t.status <> s.name
            LIMIT 1
            """,
            (entity_type,),
        ).fetchall()
        if rows:
            raise RuntimeError(
                f"Status mismatch detected in table '{table_name}': legacy status text differs from status_id mapping"
            )


def validate_status_model(conn: sqlite3.Connection) -> None:
    required = (
        ("pocket", "Запущен"),
        ("pocket", "Завершён"),
        ("project", "Активен"),
        ("project", "Завершён"),
        ("task", "Создана"),
        ("task", "В работе"),
        ("task", "Приостановлена"),
        ("task", "Завершена"),
        ("user", "Активен"),
        ("user", "Неактивен"),
    )
    for entity_type, name in required:
        row = conn.execute(
            "SELECT id FROM statuses WHERE entity_type = ? AND name = ? LIMIT 1",
            (entity_type, name),
        ).fetchone()
        if row is None:
            raise RuntimeError(f"Missing required status '{name}' for entity_type '{entity_type}'")

    for table_name in ("users", "pockets", "projects", "tasks"):
        row = conn.execute(f"SELECT id FROM {table_name} WHERE status_id IS NULL LIMIT 1").fetchone()
        if row is not None:
            raise RuntimeError(f"Null status_id detected in table '{table_name}'")

    for table_name, entity_type in (("users", "user"), ("pockets", "pocket"), ("projects", "project"), ("tasks", "task")):
        row = conn.execute(
            f"""
            SELECT t.id
            FROM {table_name} t
            JOIN statuses s ON s.id = t.status_id
            WHERE s.entity_type <> ?
            LIMIT 1
            """,
            (entity_type,),
        ).fetchone()
        if row is not None:
            raise RuntimeError(f"Invalid status_id entity_type mapping in table '{table_name}'")
