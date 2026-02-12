"""Repository layer for CRUD operations."""
from __future__ import annotations

import sqlite3
from typing import Any, Iterable
from .models import row_to_dict


class UsersRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, *, actor_user_id: int, login: str, full_name: str, role: str, is_active: int = 1) -> dict[str, Any]:
        cur = self.conn.execute(
            "INSERT INTO users (login, full_name, role, is_active) VALUES (?, ?, ?, ?)",
            (login, full_name, role, is_active),
        )
        return self.get(cur.lastrowid)

    def get(self, user_id: int) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return row_to_dict(row) if row else {}

    def list(self, *, is_active: int | None = None) -> list[dict[str, Any]]:
        if is_active is None:
            rows = self.conn.execute("SELECT * FROM users").fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM users WHERE is_active = ?", (is_active,)).fetchall()
        return [row_to_dict(r) for r in rows]

    def update(self, *, actor_user_id: int, user_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        current = self.get(user_id)
        if not current:
            return {}
        fields = []
        values = []
        for key, value in updates.items():
            fields.append(f"{key} = ?")
            values.append(value)
        values.append(user_id)
        self.conn.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", values)
        return self.get(user_id)

    def deactivate(self, *, actor_user_id: int, user_id: int) -> dict[str, Any]:
        return self.update(actor_user_id=actor_user_id, user_id=user_id, updates={"is_active": 0})


class PocketsRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, *, actor_user_id: int, data: dict[str, Any]) -> dict[str, Any]:
        cur = self.conn.execute(
            """
            INSERT INTO pockets (name, date_start, date_end, status, owner_user_id, department)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                data["name"],
                data["date_start"],
                data["date_end"],
                data["status"],
                data["owner_user_id"],
                data["department"],
            ),
        )
        return self.get(cur.lastrowid)

    def get(self, pocket_id: int) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM pockets WHERE id = ?", (pocket_id,)).fetchone()
        return row_to_dict(row) if row else {}

    def list(self, *, status: str | None = None) -> list[dict[str, Any]]:
        if status:
            rows = self.conn.execute("SELECT * FROM pockets WHERE status = ?", (status,)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM pockets").fetchall()
        return [row_to_dict(r) for r in rows]

    def update(self, *, actor_user_id: int, pocket_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        current = self.get(pocket_id)
        if not current:
            return {}
        fields = []
        values = []
        for key, value in updates.items():
            fields.append(f"{key} = ?")
            values.append(value)
        values.append(pocket_id)
        self.conn.execute(f"UPDATE pockets SET {', '.join(fields)} WHERE id = ?", values)
        return self.get(pocket_id)


class ProjectsRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, *, actor_user_id: int, data: dict[str, Any]) -> dict[str, Any]:
        cur = self.conn.execute(
            """
            INSERT INTO projects (name, pocket_id, status, date_start, date_end, curator_business_user_id, curator_it_user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["name"],
                data["pocket_id"],
                data["status"],
                data["date_start"],
                data["date_end"],
                data["curator_business_user_id"],
                data["curator_it_user_id"],
            ),
        )
        return self.get(cur.lastrowid)

    def get(self, project_id: int) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        return row_to_dict(row) if row else {}

    def list(self, *, pocket_id: int | None = None, status: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM projects"
        params: list[Any] = []
        conditions = []
        if pocket_id is not None:
            conditions.append("pocket_id = ?")
            params.append(pocket_id)
        if status:
            conditions.append("status = ?")
            params.append(status)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        rows = self.conn.execute(query, params).fetchall()
        return [row_to_dict(r) for r in rows]

    def update(self, *, actor_user_id: int, project_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        current = self.get(project_id)
        if not current:
            return {}
        fields = []
        values = []
        for key, value in updates.items():
            fields.append(f"{key} = ?")
            values.append(value)
        values.append(project_id)
        self.conn.execute(f"UPDATE projects SET {', '.join(fields)} WHERE id = ?", values)
        return self.get(project_id)


class TasksRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, *, actor_user_id: int, data: dict[str, Any]) -> dict[str, Any]:
        cur = self.conn.execute(
            """
            INSERT INTO tasks (description, project_id, status, date_created, date_start_work, date_done, executor_user_id, customer, code_link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["description"],
                data["project_id"],
                data["status"],
                data["date_created"],
                data.get("date_start_work"),
                data.get("date_done"),
                data["executor_user_id"],
                data.get("customer"),
                data.get("code_link"),
            ),
        )
        return self.get(cur.lastrowid)

    def get(self, task_id: int) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return row_to_dict(row) if row else {}

    def list(self, *, project_id: int | None = None, status: str | None = None, executor_user_id: int | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM tasks"
        params: list[Any] = []
        conditions = []
        if project_id is not None:
            conditions.append("project_id = ?")
            params.append(project_id)
        if status:
            conditions.append("status = ?")
            params.append(status)
        if executor_user_id is not None:
            conditions.append("executor_user_id = ?")
            params.append(executor_user_id)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        rows = self.conn.execute(query, params).fetchall()
        return [row_to_dict(r) for r in rows]

    def update(self, *, actor_user_id: int, task_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        current = self.get(task_id)
        if not current:
            return {}
        fields = []
        values = []
        for key, value in updates.items():
            fields.append(f"{key} = ?")
            values.append(value)
        values.append(task_id)
        self.conn.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?", values)
        return self.get(task_id)


class TaskPausesRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, *, actor_user_id: int, data: dict[str, Any]) -> dict[str, Any]:
        cur = self.conn.execute(
            """
            INSERT INTO task_pauses (task_id, date_start, date_end)
            VALUES (?, ?, ?)
            """,
            (data["task_id"], data["date_start"], data["date_end"]),
        )
        return self.get(cur.lastrowid)

    def update(self, *, actor_user_id: int, pause_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        current = self.get(pause_id)
        if not current:
            return {}
        fields = []
        values = []
        for key, value in updates.items():
            fields.append(f"{key} = ?")
            values.append(value)
        values.append(pause_id)
        self.conn.execute(f"UPDATE task_pauses SET {', '.join(fields)} WHERE id = ?", values)
        return self.get(pause_id)

    def get(self, pause_id: int) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM task_pauses WHERE id = ?", (pause_id,)).fetchone()
        return row_to_dict(row) if row else {}

    def list(self, *, task_id: int | None) -> list[dict[str, Any]]:
        if task_id is None:
            rows = self.conn.execute("SELECT * FROM task_pauses").fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM task_pauses WHERE task_id = ?", (task_id,)).fetchall()
        return [row_to_dict(r) for r in rows]

    def get_open_pause(self, task_id: int) -> dict[str, Any]:
        row = self.conn.execute(
            "SELECT * FROM task_pauses WHERE task_id = ? AND date_end IS NULL ORDER BY date_start DESC LIMIT 1",
            (task_id,),
        ).fetchone()
        return row_to_dict(row) if row else {}


class ActionLogRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def list(self, *, entity_type: str | None = None, entity_id: int | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM action_log"
        params: list[Any] = []
        conditions = []
        if entity_type:
            conditions.append("entity_type = ?")
            params.append(entity_type)
        if entity_id is not None:
            conditions.append("entity_id = ?")
            params.append(entity_id)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY timestamp ASC"
        rows = self.conn.execute(query, params).fetchall()
        return [row_to_dict(r) for r in rows]

    def get(self, log_id: int) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM action_log WHERE id = ?", (log_id,)).fetchone()
        return row_to_dict(row) if row else {}
