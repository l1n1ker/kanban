"""Service layer with permission checks and WIP calculation."""
from __future__ import annotations

from typing import Any
import sqlite3

from .logging import format_changes, log_action
from .rbac import check_permission
from .repositories import UsersRepo, PocketsRepo, ProjectsRepo, TasksRepo, TaskPausesRepo, ActionLogRepo


class Services:
    def __init__(self, conn: sqlite3.Connection, *, actor_user: dict[str, Any]) -> None:
        self.conn = conn
        self.actor_user = actor_user
        self.users = UsersRepo(conn)
        self.pockets = PocketsRepo(conn)
        self.projects = ProjectsRepo(conn)
        self.tasks = TasksRepo(conn)
        self.task_pauses = TaskPausesRepo(conn)
        self.action_log = ActionLogRepo(conn)
        self._valid_task_statuses = {"Создана", "В работе", "Приостановлена", "Завершена"}
        self._task_transitions = {
            "Создана": {"В работе"},
            "В работе": {"Приостановлена", "Завершена"},
            "Приостановлена": {"В работе"},
        }

    def _check(self, action: str) -> None:
        check_permission(self.actor_user["role"], action)

    def _log(self, *, entity_type: str, entity_id: int, action_type: str, old: dict[str, Any] | None, new: dict[str, Any] | None) -> None:
        old_text, new_text = format_changes(old, new)
        log_action(
            self.conn,
            user_id=self.actor_user["id"],
            entity_type=entity_type,
            entity_id=entity_id,
            action_type=action_type,
            old_value=old_text,
            new_value=new_text,
        )

    def _action_type_for_update(self, updates: dict[str, Any]) -> str:
        if "status" in updates:
            return "update_status"
        if any(key.endswith("_user_id") for key in updates.keys()):
            return "assign"
        return "edit"

    def _validate_task_status_update(self, current_status: str, new_status: str) -> None:
        if new_status not in self._valid_task_statuses:
            raise ValueError(f"Invalid task status: {new_status}")
        allowed = self._task_transitions.get(current_status, set())
        if new_status not in allowed:
            raise ValueError(f"Invalid task transition: {current_status} -> {new_status}")

    # Users
    def create_user(self, **data: Any) -> dict[str, Any]:
        self._check("users.create")
        result = self.users.create(actor_user_id=self.actor_user["id"], **data)
        if result:
            self._log(entity_type="user", entity_id=result["id"], action_type="create", old=None, new=result)
        return result

    def list_users(self, *, is_active: int | None = None) -> list[dict[str, Any]]:
        self._check("users.list")
        return self.users.list(is_active=is_active)

    def get_user(self, user_id: int) -> dict[str, Any]:
        self._check("users.read")
        return self.users.get(user_id)

    def update_user(self, user_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        self._check("users.update")
        current = self.users.get(user_id)
        result = self.users.update(actor_user_id=self.actor_user["id"], user_id=user_id, updates=updates)
        if result:
            self._log(entity_type="user", entity_id=user_id, action_type="edit", old=current, new=result)
        return result

    def deactivate_user(self, user_id: int) -> dict[str, Any]:
        self._check("users.delete")
        current = self.users.get(user_id)
        result = self.users.deactivate(actor_user_id=self.actor_user["id"], user_id=user_id)
        if result:
            self._log(entity_type="user", entity_id=user_id, action_type="edit", old=current, new=result)
        return result

    # Pockets
    def create_pocket(self, data: dict[str, Any]) -> dict[str, Any]:
        self._check("pockets.create")
        result = self.pockets.create(actor_user_id=self.actor_user["id"], data=data)
        if result:
            self._log(entity_type="pocket", entity_id=result["id"], action_type="create", old=None, new=result)
        return result

    def list_pockets(self, *, status: str | None = None) -> list[dict[str, Any]]:
        self._check("pockets.list")
        return self.pockets.list(status=status)

    def update_pocket(self, pocket_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        self._check("pockets.update")
        current = self.pockets.get(pocket_id)
        result = self.pockets.update(actor_user_id=self.actor_user["id"], pocket_id=pocket_id, updates=updates)
        if result:
            action_type = self._action_type_for_update(updates)
            self._log(entity_type="pocket", entity_id=pocket_id, action_type=action_type, old=current, new=result)
        return result

    # Projects
    def create_project(self, data: dict[str, Any]) -> dict[str, Any]:
        self._check("projects.create")
        result = self.projects.create(actor_user_id=self.actor_user["id"], data=data)
        if result:
            self._log(entity_type="project", entity_id=result["id"], action_type="create", old=None, new=result)
        return result

    def list_projects(self, *, pocket_id: int | None = None, status: str | None = None) -> list[dict[str, Any]]:
        self._check("projects.list")
        return self.projects.list(pocket_id=pocket_id, status=status)

    def update_project(self, project_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        self._check("projects.update")
        current = self.projects.get(project_id)
        result = self.projects.update(actor_user_id=self.actor_user["id"], project_id=project_id, updates=updates)
        if result:
            action_type = self._action_type_for_update(updates)
            self._log(entity_type="project", entity_id=project_id, action_type=action_type, old=current, new=result)
        return result

    # Tasks
    def create_task(self, data: dict[str, Any]) -> dict[str, Any]:
        self._check("tasks.create")
        if data.get("status") != "Создана":
            raise ValueError("New task must start with status 'Создана'")
        result = self.tasks.create(actor_user_id=self.actor_user["id"], data=data)
        if result:
            self._log(entity_type="task", entity_id=result["id"], action_type="create", old=None, new=result)
        return result

    def list_tasks(self, *, project_id: int | None = None, status: str | None = None, executor_user_id: int | None = None) -> list[dict[str, Any]]:
        self._check("tasks.list")
        return self.tasks.list(project_id=project_id, status=status, executor_user_id=executor_user_id)

    def update_task(self, task_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        self._check("tasks.update")
        current = self.tasks.get(task_id)
        if not current:
            return {}
        if "status" in updates:
            self._validate_task_status_update(current.get("status"), updates["status"])
        result = self.tasks.update(actor_user_id=self.actor_user["id"], task_id=task_id, updates=updates)
        if result:
            action_type = self._action_type_for_update(updates)
            self._log(entity_type="task", entity_id=task_id, action_type=action_type, old=current, new=result)
        return result

    def add_task_pause(self, data: dict[str, Any]) -> dict[str, Any]:
        self._check("task_pauses.create")
        result = self.task_pauses.create(actor_user_id=self.actor_user["id"], data=data)
        if result:
            self._log(entity_type="task", entity_id=data["task_id"], action_type="pause_start", old=None, new=result)
        return result

    def end_task_pause(self, pause_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        self._check("task_pauses.create")
        current = self.task_pauses.get(pause_id)
        if current and "date_end" in updates and updates["date_end"] < current["date_start"]:
            raise ValueError("date_end cannot be earlier than date_start")
        result = self.task_pauses.update(actor_user_id=self.actor_user["id"], pause_id=pause_id, updates=updates)
        if result:
            self._log(entity_type="task", entity_id=result["task_id"], action_type="pause_end", old=current, new=result)
        return result

    def list_task_pauses(self, task_id: int) -> list[dict[str, Any]]:
        self._check("task_pauses.list")
        return self.task_pauses.list(task_id=task_id)

    # Logs
    def list_action_log(self, *, entity_type: str | None = None, entity_id: int | None = None) -> list[dict[str, Any]]:
        self._check("action_log.list")
        return self.action_log.list(entity_type=entity_type, entity_id=entity_id)

    # WIP
    def wip_for_task(self, task_id: int) -> int:
        task = self.tasks.get(task_id)
        return 1 if task and task.get("status") == "В работе" else 0

    def wip_for_project(self, project_id: int) -> int:
        rows = self.conn.execute(
            "SELECT COUNT(*) AS cnt FROM tasks WHERE project_id = ? AND status = ?",
            (project_id, "В работе"),
        ).fetchone()
        return int(rows["cnt"]) if rows else 0

    def wip_for_pocket(self, pocket_id: int) -> int:
        rows = self.conn.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM tasks t
            JOIN projects p ON p.id = t.project_id
            WHERE p.pocket_id = ? AND t.status = ?
            """,
            (pocket_id, "В работе"),
        ).fetchone()
        return int(rows["cnt"]) if rows else 0
