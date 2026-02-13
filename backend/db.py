"""SQLite connection and schema initialization."""
from __future__ import annotations

import os
import sqlite3

DB_PATH = os.getenv("KANBAN_DB_PATH", "kanban.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
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

def _tasks_executor_is_notnull(conn: sqlite3.Connection) -> bool:
    try:
        rows = conn.execute("PRAGMA table_info(tasks)").fetchall()
    except sqlite3.Error:
        return False
    for row in rows:
        # row: cid, name, type, notnull, dflt_value, pk
        if row[1] == "executor_user_id":
            return bool(row[3])
    return False


def _migrate_tasks_executor_nullable(conn: sqlite3.Connection) -> None:
    if not _tasks_executor_is_notnull(conn):
        return
    conn.executescript(
        """
        PRAGMA foreign_keys=off;
        BEGIN;

        CREATE TABLE tasks_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            project_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            date_created TEXT NOT NULL,
            date_start_work TEXT,
            date_done TEXT,
            executor_user_id INTEGER,
            customer TEXT,
            code_link TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(executor_user_id) REFERENCES users(id),
            FOREIGN KEY(status) REFERENCES task_statuses(name)
        );

        INSERT INTO tasks_new (id, description, project_id, status, date_created, date_start_work, date_done, executor_user_id, customer, code_link)
        SELECT id, description, project_id, status, date_created, date_start_work, date_done, executor_user_id, customer, code_link
        FROM tasks;

        DROP TABLE tasks;
        ALTER TABLE tasks_new RENAME TO tasks;

        COMMIT;
        PRAGMA foreign_keys=on;
        """
    )


def _projects_has_project_code(conn: sqlite3.Connection) -> bool:
    try:
        rows = conn.execute("PRAGMA table_info(projects)").fetchall()
    except sqlite3.Error:
        return False
    for row in rows:
        if row[1] == "project_code":
            return True
    return False


def _migrate_projects_add_project_code(conn: sqlite3.Connection) -> None:
    if _projects_has_project_code(conn):
        return
    conn.execute("ALTER TABLE projects ADD COLUMN project_code TEXT")


def _table_has_column(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in rows)


def _migrate_statuses_model(conn: sqlite3.Connection) -> None:
    if not _table_has_column(conn, "users", "status_id"):
        conn.execute("ALTER TABLE users ADD COLUMN status_id INTEGER")
    if not _table_has_column(conn, "pockets", "status_id"):
        conn.execute("ALTER TABLE pockets ADD COLUMN status_id INTEGER")
    if not _table_has_column(conn, "projects", "status_id"):
        conn.execute("ALTER TABLE projects ADD COLUMN status_id INTEGER")
    if not _table_has_column(conn, "tasks", "status_id"):
        conn.execute("ALTER TABLE tasks ADD COLUMN status_id INTEGER")

    # Backfill entity status ids from legacy text columns.
    conn.execute(
        """
        UPDATE pockets
        SET status_id = (
            SELECT s.id FROM statuses s WHERE s.entity_type = 'pocket' AND s.name = pockets.status LIMIT 1
        )
        WHERE status_id IS NULL
        """
    )
    conn.execute(
        """
        UPDATE projects
        SET status_id = (
            SELECT s.id FROM statuses s WHERE s.entity_type = 'project' AND s.name = projects.status LIMIT 1
        )
        WHERE status_id IS NULL
        """
    )
    conn.execute(
        """
        UPDATE tasks
        SET status_id = (
            SELECT s.id FROM statuses s WHERE s.entity_type = 'task' AND s.name = tasks.status LIMIT 1
        )
        WHERE status_id IS NULL
        """
    )
    conn.execute(
        """
        UPDATE users
        SET status_id = (
            SELECT s.id FROM statuses s
            WHERE s.entity_type = 'user'
              AND s.name = CASE WHEN users.is_active = 1 THEN 'Активен' ELSE 'Неактивен' END
            LIMIT 1
        )
        WHERE status_id IS NULL
        """
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
            is_active INTEGER NOT NULL DEFAULT 1,
            status_id INTEGER,
            FOREIGN KEY(status_id) REFERENCES statuses(id)
        );

        CREATE TABLE IF NOT EXISTS pockets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            date_start TEXT NOT NULL,
            date_end TEXT,
            status TEXT NOT NULL,
            status_id INTEGER,
            owner_user_id INTEGER NOT NULL,
            department TEXT NOT NULL,
            FOREIGN KEY(owner_user_id) REFERENCES users(id),
            FOREIGN KEY(status) REFERENCES pocket_statuses(name),
            FOREIGN KEY(status_id) REFERENCES statuses(id)
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            project_code TEXT,
            pocket_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            status_id INTEGER,
            date_start TEXT NOT NULL,
            date_end TEXT,
            curator_business_user_id INTEGER NOT NULL,
            curator_it_user_id INTEGER NOT NULL,
            FOREIGN KEY(pocket_id) REFERENCES pockets(id),
            FOREIGN KEY(curator_business_user_id) REFERENCES users(id),
            FOREIGN KEY(curator_it_user_id) REFERENCES users(id),
            FOREIGN KEY(status) REFERENCES project_statuses(name),
            FOREIGN KEY(status_id) REFERENCES statuses(id)
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            project_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            status_id INTEGER,
            date_created TEXT NOT NULL,
            date_start_work TEXT,
            date_done TEXT,
            executor_user_id INTEGER,
            customer TEXT,
            code_link TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(executor_user_id) REFERENCES users(id),
            FOREIGN KEY(status) REFERENCES task_statuses(name),
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

        CREATE TABLE IF NOT EXISTS pocket_statuses (
            name TEXT PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS project_statuses (
            name TEXT PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS task_statuses (
            name TEXT PRIMARY KEY
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

    _migrate_tasks_executor_nullable(conn)
    _migrate_projects_add_project_code(conn)
    _seed_reference_data(conn)
    _migrate_statuses_model(conn)
    conn.commit()
    conn.close()
