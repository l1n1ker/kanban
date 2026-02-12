"""SQLite connection and schema initialization."""
from __future__ import annotations

import os
import sqlite3

DB_PATH = os.getenv("KANBAN_DB_PATH", "kanban.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _seed_reference_data(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT OR IGNORE INTO pocket_statuses(name) VALUES (?)",
        [("Запущен",), ("Завершён",)],
    )
    conn.executemany(
        "INSERT OR IGNORE INTO project_statuses(name) VALUES (?)",
        [("Активен",), ("Завершён",)],
    )
    conn.executemany(
        "INSERT OR IGNORE INTO task_statuses(name) VALUES (?)",
        [("Создана",), ("В работе",), ("Приостановлена",), ("Завершена",)],
    )


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS pockets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            date_start TEXT NOT NULL,
            date_end TEXT NOT NULL,
            status TEXT NOT NULL,
            owner_user_id INTEGER NOT NULL,
            department TEXT NOT NULL,
            FOREIGN KEY(owner_user_id) REFERENCES users(id),
            FOREIGN KEY(status) REFERENCES pocket_statuses(name)
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            pocket_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            date_start TEXT NOT NULL,
            date_end TEXT NOT NULL,
            curator_business_user_id INTEGER NOT NULL,
            curator_it_user_id INTEGER NOT NULL,
            FOREIGN KEY(pocket_id) REFERENCES pockets(id),
            FOREIGN KEY(curator_business_user_id) REFERENCES users(id),
            FOREIGN KEY(curator_it_user_id) REFERENCES users(id),
            FOREIGN KEY(status) REFERENCES project_statuses(name)
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            project_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            date_created TEXT NOT NULL,
            date_start_work TEXT,
            date_done TEXT,
            executor_user_id INTEGER NOT NULL,
            customer TEXT,
            code_link TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(executor_user_id) REFERENCES users(id),
            FOREIGN KEY(status) REFERENCES task_statuses(name)
        );

        CREATE TABLE IF NOT EXISTS task_pauses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            date_start TEXT NOT NULL,
            date_end TEXT NOT NULL,
            FOREIGN KEY(task_id) REFERENCES tasks(id)
        );

        CREATE TABLE IF NOT EXISTS action_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            comment TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS pocket_statuses (
            name TEXT PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS project_statuses (
            name TEXT PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS task_statuses (
            name TEXT PRIMARY KEY
        );
        """
    )

    _seed_reference_data(conn)
    conn.commit()
    conn.close()
