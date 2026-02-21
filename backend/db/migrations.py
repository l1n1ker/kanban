"""Database migrations."""
from __future__ import annotations

import sqlite3


def _table_has_column(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in rows)


def _tasks_executor_is_notnull(conn: sqlite3.Connection) -> bool:
    try:
        rows = conn.execute("PRAGMA table_info(tasks)").fetchall()
    except sqlite3.Error:
        return False
    for row in rows:
        if row[1] == "executor_user_id":
            return bool(row[3])
    return False


def migrate_tasks_executor_nullable(conn: sqlite3.Connection) -> None:
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

        INSERT INTO tasks_new (id, description, project_id, status_id, date_created, date_start_work, date_done, executor_user_id, customer, code_link)
        SELECT
            t.id,
            t.description,
            t.project_id,
            COALESCE(
                t.status_id,
                (SELECT s.id FROM statuses s WHERE s.entity_type = 'task' AND s.name = t.status LIMIT 1),
                (SELECT s.id FROM statuses s WHERE s.entity_type = 'task' AND s.name = 'Создана' LIMIT 1)
            ) AS status_id,
            t.date_created,
            t.date_start_work,
            t.date_done,
            t.executor_user_id,
            t.customer,
            t.code_link
        FROM tasks t;

        DROP TABLE tasks;
        ALTER TABLE tasks_new RENAME TO tasks;

        COMMIT;
        PRAGMA foreign_keys=on;
        """
    )


def migrate_projects_add_project_code(conn: sqlite3.Connection) -> None:
    rows = conn.execute("PRAGMA table_info(projects)").fetchall()
    if any(row[1] == "project_code" for row in rows):
        return
    conn.execute("ALTER TABLE projects ADD COLUMN project_code TEXT")


def migrate_statuses_model(conn: sqlite3.Connection) -> None:
    if not _table_has_column(conn, "users", "status_id"):
        conn.execute("ALTER TABLE users ADD COLUMN status_id INTEGER")
    if not _table_has_column(conn, "pockets", "status_id"):
        conn.execute("ALTER TABLE pockets ADD COLUMN status_id INTEGER")
    if not _table_has_column(conn, "projects", "status_id"):
        conn.execute("ALTER TABLE projects ADD COLUMN status_id INTEGER")
    if not _table_has_column(conn, "tasks", "status_id"):
        conn.execute("ALTER TABLE tasks ADD COLUMN status_id INTEGER")

    if _table_has_column(conn, "pockets", "status"):
        conn.execute(
            """
            UPDATE pockets
            SET status_id = (
                SELECT s.id FROM statuses s WHERE s.entity_type = 'pocket' AND s.name = pockets.status LIMIT 1
            )
            WHERE status_id IS NULL
            """
        )
    if _table_has_column(conn, "projects", "status"):
        conn.execute(
            """
            UPDATE projects
            SET status_id = (
                SELECT s.id FROM statuses s WHERE s.entity_type = 'project' AND s.name = projects.status LIMIT 1
            )
            WHERE status_id IS NULL
            """
        )
    if _table_has_column(conn, "tasks", "status"):
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


def table_has_column(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    return _table_has_column(conn, table_name, column_name)
