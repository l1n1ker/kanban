"""Reference data seed routines."""
from __future__ import annotations

import sqlite3


def seed_reference_data(conn: sqlite3.Connection) -> None:
    conn.executemany(
        """
        INSERT OR IGNORE INTO statuses(entity_type, code, name, is_active, sort_order, is_system)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            ("pocket", "running", "Запущен", 1, 10, 1),
            ("pocket", "done", "Завершён", 1, 20, 1),
            ("project", "active", "Активен", 1, 10, 1),
            ("project", "done", "Завершён", 1, 20, 1),
            ("task", "created", "Создана", 1, 10, 1),
            ("task", "in_progress", "В работе", 1, 20, 1),
            ("task", "paused", "Приостановлена", 1, 30, 1),
            ("task", "done", "Завершена", 1, 40, 1),
            ("user", "active", "Активен", 1, 10, 1),
            ("user", "inactive", "Неактивен", 1, 20, 1),
        ],
    )
