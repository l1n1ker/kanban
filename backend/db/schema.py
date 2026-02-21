"""Schema creation SQL."""
from __future__ import annotations

import sqlite3


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            status_id INTEGER,
            FOREIGN KEY(status_id) REFERENCES statuses(id)
        );

        CREATE TABLE IF NOT EXISTS pockets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            date_start TEXT NOT NULL,
            date_end TEXT,
            status_id INTEGER NOT NULL,
            owner_user_id INTEGER NOT NULL,
            department TEXT NOT NULL,
            FOREIGN KEY(owner_user_id) REFERENCES users(id),
            FOREIGN KEY(status_id) REFERENCES statuses(id)
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            project_code TEXT,
            pocket_id INTEGER NOT NULL,
            status_id INTEGER NOT NULL,
            date_start TEXT NOT NULL,
            date_end TEXT,
            curator_business_user_id INTEGER NOT NULL,
            curator_it_user_id INTEGER NOT NULL,
            FOREIGN KEY(pocket_id) REFERENCES pockets(id),
            FOREIGN KEY(curator_business_user_id) REFERENCES users(id),
            FOREIGN KEY(curator_it_user_id) REFERENCES users(id),
            FOREIGN KEY(status_id) REFERENCES statuses(id)
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            project_id INTEGER NOT NULL,
            status_id INTEGER NOT NULL,
            date_created TEXT NOT NULL,
            date_start_work TEXT,
            date_done TEXT,
            executor_user_id INTEGER,
            customer TEXT,
            code_link TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(executor_user_id) REFERENCES users(id),
            FOREIGN KEY(status_id) REFERENCES statuses(id)
        );

        CREATE TABLE IF NOT EXISTS task_pauses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            date_start TEXT NOT NULL,
            date_end TEXT,
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

        CREATE TABLE IF NOT EXISTS statuses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            sort_order INTEGER NOT NULL DEFAULT 100,
            is_system INTEGER NOT NULL DEFAULT 0,
            UNIQUE(entity_type, code),
            UNIQUE(entity_type, name)
        );
        """
    )
