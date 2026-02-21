"""Repository layer for CRUD operations."""
from __future__ import annotations

import sqlite3
from typing import Any

from .common import build_update_sql, fetch_all, fetch_one


def _require_lastrowid(cur: sqlite3.Cursor) -> int:
    if cur.lastrowid is None:
        raise RuntimeError("Failed to read inserted row id")
    return int(cur.lastrowid)


class UsersRepo:
    _allowed_update_fields = {"full_name", "role", "is_active", "status_id"}

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(
        self,
        *,
        actor_user_id: int,
        login: str,
        full_name: str,
        role: str,
        is_active: int = 1,
        status_id: int | None = None,
    ) -> dict[str, Any]:
        cur = self.conn.execute(
            "INSERT INTO users (login, full_name, role, is_active, status_id) VALUES (?, ?, ?, ?, ?)",
            (login, full_name, role, is_active, status_id),
        )
        return self.get(_require_lastrowid(cur))

    def get(self, user_id: int) -> dict[str, Any]:
        return fetch_one(self.conn, "SELECT * FROM users WHERE id = ?", (user_id,))

    def list(self, *, is_active: int | None = None) -> list[dict[str, Any]]:
        if is_active is None:
            return fetch_all(self.conn, "SELECT * FROM users", ())
        return fetch_all(self.conn, "SELECT * FROM users WHERE is_active = ?", (is_active,))

    def update(self, *, actor_user_id: int, user_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        current = self.get(user_id)
        if not current:
            return {}
        fields_sql, values = build_update_sql(updates=updates, allowed_fields=self._allowed_update_fields)
        self.conn.execute(f"UPDATE users SET {fields_sql} WHERE id = ?", [*values, user_id])
        return self.get(user_id)

    def deactivate(self, *, actor_user_id: int, user_id: int) -> dict[str, Any]:
        return self.update(actor_user_id=actor_user_id, user_id=user_id, updates={"is_active": 0})


class PocketsRepo:
    _allowed_update_fields = {"name", "date_start", "date_end", "status_id", "owner_user_id", "department"}

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, *, actor_user_id: int, data: dict[str, Any]) -> dict[str, Any]:
        cur = self.conn.execute(
            """
            INSERT INTO pockets (name, date_start, date_end, status_id, owner_user_id, department)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                data["name"],
                data["date_start"],
                data["date_end"],
                data.get("status_id"),
                data["owner_user_id"],
                data["department"],
            ),
        )
        return self.get(_require_lastrowid(cur))

    def get(self, pocket_id: int) -> dict[str, Any]:
        return fetch_one(self.conn, "SELECT * FROM pockets WHERE id = ?", (pocket_id,))

    def list(self, *, status_id: int | None = None) -> list[dict[str, Any]]:
        if status_id is not None:
            return fetch_all(self.conn, "SELECT * FROM pockets WHERE status_id = ?", (status_id,))
        return fetch_all(self.conn, "SELECT * FROM pockets", ())

    def update(self, *, actor_user_id: int, pocket_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        current = self.get(pocket_id)
        if not current:
            return {}
        fields_sql, values = build_update_sql(updates=updates, allowed_fields=self._allowed_update_fields)
        self.conn.execute(f"UPDATE pockets SET {fields_sql} WHERE id = ?", [*values, pocket_id])
        return self.get(pocket_id)


class ProjectsRepo:
    _allowed_update_fields = {
        "name",
        "project_code",
        "pocket_id",
        "status_id",
        "date_start",
        "date_end",
        "curator_business_user_id",
        "curator_it_user_id",
    }

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, *, actor_user_id: int, data: dict[str, Any]) -> dict[str, Any]:
        cur = self.conn.execute(
            """
            INSERT INTO projects (name, project_code, pocket_id, status_id, date_start, date_end, curator_business_user_id, curator_it_user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["name"],
                data.get("project_code"),
                data["pocket_id"],
                data.get("status_id"),
                data["date_start"],
                data["date_end"],
                data["curator_business_user_id"],
                data["curator_it_user_id"],
            ),
        )
        return self.get(_require_lastrowid(cur))

    def get(self, project_id: int) -> dict[str, Any]:
        return fetch_one(self.conn, "SELECT * FROM projects WHERE id = ?", (project_id,))

    def list(
        self,
        *,
        pocket_id: int | None = None,
        status_id: int | None = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM projects"
        params: list[Any] = []
        conditions = []
        if pocket_id is not None:
            conditions.append("pocket_id = ?")
            params.append(pocket_id)
        if status_id is not None:
            conditions.append("status_id = ?")
            params.append(status_id)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        return fetch_all(self.conn, query, params)

    def update(self, *, actor_user_id: int, project_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        current = self.get(project_id)
        if not current:
            return {}
        fields_sql, values = build_update_sql(updates=updates, allowed_fields=self._allowed_update_fields)
        self.conn.execute(f"UPDATE projects SET {fields_sql} WHERE id = ?", [*values, project_id])
        return self.get(project_id)


class TasksRepo:
    _allowed_update_fields = {
        "description",
        "project_id",
        "status_id",
        "date_created",
        "date_start_work",
        "date_done",
        "executor_user_id",
        "customer",
        "code_link",
    }

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, *, actor_user_id: int, data: dict[str, Any]) -> dict[str, Any]:
        cur = self.conn.execute(
            """
            INSERT INTO tasks (description, project_id, status_id, date_created, date_start_work, date_done, executor_user_id, customer, code_link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["description"],
                data["project_id"],
                data.get("status_id"),
                data["date_created"],
                data.get("date_start_work"),
                data.get("date_done"),
                data.get("executor_user_id"),
                data.get("customer"),
                data.get("code_link"),
            ),
        )
        return self.get(_require_lastrowid(cur))

    def get(self, task_id: int) -> dict[str, Any]:
        return fetch_one(self.conn, "SELECT * FROM tasks WHERE id = ?", (task_id,))

    def list(
        self,
        *,
        project_id: int | None = None,
        status_id: int | None = None,
        executor_user_id: int | None = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM tasks"
        params: list[Any] = []
        conditions = []
        if project_id is not None:
            conditions.append("project_id = ?")
            params.append(project_id)
        if status_id is not None:
            conditions.append("status_id = ?")
            params.append(status_id)
        if executor_user_id is not None:
            conditions.append("executor_user_id = ?")
            params.append(executor_user_id)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        return fetch_all(self.conn, query, params)

    def update(self, *, actor_user_id: int, task_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        current = self.get(task_id)
        if not current:
            return {}
        fields_sql, values = build_update_sql(updates=updates, allowed_fields=self._allowed_update_fields)
        self.conn.execute(f"UPDATE tasks SET {fields_sql} WHERE id = ?", [*values, task_id])
        return self.get(task_id)


class TaskPausesRepo:
    _allowed_update_fields = {"date_end"}

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, *, actor_user_id: int, data: dict[str, Any]) -> dict[str, Any]:
        cur = self.conn.execute(
            "INSERT INTO task_pauses (task_id, date_start, date_end) VALUES (?, ?, ?)",
            (data["task_id"], data["date_start"], data.get("date_end")),
        )
        return self.get(_require_lastrowid(cur))

    def get(self, pause_id: int) -> dict[str, Any]:
        return fetch_one(self.conn, "SELECT * FROM task_pauses WHERE id = ?", (pause_id,))

    def get_open_pause(self, task_id: int) -> dict[str, Any]:
        return fetch_one(
            self.conn,
            "SELECT * FROM task_pauses WHERE task_id = ? AND date_end IS NULL ORDER BY id DESC LIMIT 1",
            (task_id,),
        )

    def list(self, *, task_id: int | None = None) -> list[dict[str, Any]]:
        if task_id is None:
            return fetch_all(self.conn, "SELECT * FROM task_pauses", ())
        return fetch_all(self.conn, "SELECT * FROM task_pauses WHERE task_id = ?", (task_id,))

    def update(self, *, actor_user_id: int, pause_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        current = self.get(pause_id)
        if not current:
            return {}
        fields_sql, values = build_update_sql(updates=updates, allowed_fields=self._allowed_update_fields)
        self.conn.execute(f"UPDATE task_pauses SET {fields_sql} WHERE id = ?", [*values, pause_id])
        return self.get(pause_id)


class ActionLogRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get(self, log_id: int) -> dict[str, Any]:
        return fetch_one(self.conn, "SELECT * FROM action_log WHERE id = ?", (log_id,))

    def list(self, *, entity_type: str | None = None, entity_id: int | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM action_log"
        params: list[Any] = []
        conditions = []
        if entity_type is not None:
            conditions.append("entity_type = ?")
            params.append(entity_type)
        if entity_id is not None:
            conditions.append("entity_id = ?")
            params.append(entity_id)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY id"
        return fetch_all(self.conn, query, params)


class StatusesRepo:
    _allowed_update_fields = {"code", "name", "is_active", "sort_order"}

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, *, actor_user_id: int, data: dict[str, Any]) -> dict[str, Any]:
        cur = self.conn.execute(
            """
            INSERT INTO statuses (entity_type, code, name, is_active, sort_order, is_system)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                data["entity_type"],
                data["code"],
                data["name"],
                int(data.get("is_active", 1)),
                int(data.get("sort_order", 100)),
                int(data.get("is_system", 0)),
            ),
        )
        return self.get(_require_lastrowid(cur))

    def get(self, status_id: int) -> dict[str, Any]:
        return fetch_one(self.conn, "SELECT * FROM statuses WHERE id = ?", (status_id,))

    def find_by_name(self, *, entity_type: str, name: str) -> dict[str, Any]:
        return fetch_one(
            self.conn,
            "SELECT * FROM statuses WHERE entity_type = ? AND name = ? LIMIT 1",
            (entity_type, name),
        )

    def list(self, *, entity_type: str | None = None, is_active: int | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM statuses"
        params: list[Any] = []
        conditions = []
        if entity_type is not None:
            conditions.append("entity_type = ?")
            params.append(entity_type)
        if is_active is not None:
            conditions.append("is_active = ?")
            params.append(int(is_active))
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY entity_type, sort_order, id"
        return fetch_all(self.conn, query, params)

    def update(self, *, actor_user_id: int, status_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        current = self.get(status_id)
        if not current:
            return {}
        fields_sql, values = build_update_sql(updates=updates, allowed_fields=self._allowed_update_fields)
        self.conn.execute(f"UPDATE statuses SET {fields_sql} WHERE id = ?", [*values, status_id])
        return self.get(status_id)

    def delete(self, *, actor_user_id: int, status_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM statuses WHERE id = ?", (status_id,))
        return cur.rowcount > 0
