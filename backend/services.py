"""Service layer with permission checks and WIP calculation."""
from __future__ import annotations

from typing import Any
from datetime import date
import sqlite3

from .logging import format_changes, log_action
from .rbac import check_permission
from .repositories import (
    UsersRepo,
    PocketsRepo,
    ProjectsRepo,
    TasksRepo,
    TaskPausesRepo,
    ActionLogRepo,
    StatusesRepo,
)


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
        self.statuses = StatusesRepo(conn)
        self._valid_task_statuses = {"Создана", "В работе", "Приостановлена", "Завершена"}
        self._task_transitions = {
            "Создана": {"В работе"},
            "В работе": {"Приостановлена", "Завершена"},
            "Приостановлена": {"В работе"},
        }

    def _check(self, action: str) -> None:
        check_permission(self.actor_user["role"], action)

    def _log(
        self,
        *,
        entity_type: str,
        entity_id: int,
        action_type: str,
        old: dict[str, Any] | None,
        new: dict[str, Any] | None,
        comment: str | None = None,
    ) -> None:
        old_text, new_text = format_changes(old, new)
        log_action(
            self.conn,
            user_id=self.actor_user["id"],
            entity_type=entity_type,
            entity_id=entity_id,
            action_type=action_type,
            old_value=old_text,
            new_value=new_text,
            comment=comment,
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

    def _status_id_by_name(self, *, entity_type: str, name: str) -> int | None:
        found = self.statuses.find_by_name(entity_type=entity_type, name=name)
        return int(found["id"]) if found else None

    def _status_name_by_id(self, *, entity_type: str, status_id: int | None) -> str | None:
        if status_id is None:
            return None
        item = self.statuses.get(int(status_id))
        if not item:
            return None
        if item.get("entity_type") != entity_type:
            raise ValueError(f"Status id {status_id} does not belong to entity_type {entity_type}")
        return str(item["name"])

    def _attach_status_name(self, *, entity_type: str, item: dict[str, Any]) -> dict[str, Any]:
        if not item:
            return item
        status_id = item.get("status_id")
        if entity_type == "user":
            if status_id is not None:
                name = self._status_name_by_id(entity_type="user", status_id=int(status_id))
                if name:
                    item["status_name"] = name
            else:
                item["status_name"] = "Активен" if int(item.get("is_active", 0)) == 1 else "Неактивен"
            return item
        if status_id is not None:
            name = self._status_name_by_id(entity_type=entity_type, status_id=int(status_id))
            if name:
                item["status_name"] = name
                item["status"] = name
        elif item.get("status"):
            sid = self._status_id_by_name(entity_type=entity_type, name=str(item["status"]))
            if sid is not None:
                item["status_id"] = sid
                item["status_name"] = item["status"]
        return item

    def _normalize_status_payload(self, *, entity_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(payload)
        if "status_id" in normalized and normalized.get("status_id") is not None:
            name = self._status_name_by_id(entity_type=entity_type, status_id=int(normalized["status_id"]))
            if not name:
                raise ValueError(f"Unknown status_id {normalized['status_id']}")
            normalized["status"] = name
        elif "status" in normalized and normalized.get("status"):
            sid = self._status_id_by_name(entity_type=entity_type, name=str(normalized["status"]))
            if sid is not None:
                normalized["status_id"] = sid
        return normalized

    def _validate_pocket_dates(
        self,
        *,
        date_start_value: str | None,
        date_end_value: str | None,
    ) -> None:
        if not date_start_value:
            return
        if not date_end_value:
            return
        start = date.fromisoformat(date_start_value)
        end = date.fromisoformat(date_end_value)
        if end < start:
            raise ValueError("date_end cannot be earlier than date_start")

    def _as_iso_date_or_none(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text or text.lower() == "none":
            return None
        return text

    # Users
    def create_user(self, **data: Any) -> dict[str, Any]:
        self._check("users.create")
        data = self._normalize_status_payload(entity_type="user", payload=dict(data))
        if "status" in data:
            data.pop("status", None)
        if "status_id" in data and data.get("status_id") is not None:
            status_name = self._status_name_by_id(entity_type="user", status_id=int(data["status_id"]))
            data["is_active"] = 1 if status_name == "Активен" else 0
        elif "is_active" in data:
            data["status_id"] = self._status_id_by_name(
                entity_type="user",
                name="Активен" if int(data.get("is_active", 0)) == 1 else "Неактивен",
            )
        result = self.users.create(actor_user_id=self.actor_user["id"], **data)
        if result:
            self._log(entity_type="user", entity_id=result["id"], action_type="create", old=None, new=result)
        return self._attach_status_name(entity_type="user", item=result)

    def list_users(self, *, is_active: int | None = None) -> list[dict[str, Any]]:
        self._check("users.list")
        rows = self.users.list(is_active=is_active)
        return [self._attach_status_name(entity_type="user", item=row) for row in rows]

    def get_user(self, user_id: int) -> dict[str, Any]:
        self._check("users.read")
        return self._attach_status_name(entity_type="user", item=self.users.get(user_id))

    def update_user(self, user_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        self._check("users.update")
        updates = self._normalize_status_payload(entity_type="user", payload=updates)
        if "status" in updates:
            updates.pop("status", None)
        if "status_id" in updates and updates.get("status_id") is not None:
            status_name = self._status_name_by_id(entity_type="user", status_id=int(updates["status_id"]))
            updates["is_active"] = 1 if status_name == "Активен" else 0
        elif "is_active" in updates:
            updates["status_id"] = self._status_id_by_name(
                entity_type="user",
                name="Активен" if int(updates.get("is_active", 0)) == 1 else "Неактивен",
            )
        current = self.users.get(user_id)
        result = self.users.update(actor_user_id=self.actor_user["id"], user_id=user_id, updates=updates)
        if result:
            self._log(entity_type="user", entity_id=user_id, action_type="edit", old=current, new=result)
        return self._attach_status_name(entity_type="user", item=result)

    def deactivate_user(self, user_id: int) -> dict[str, Any]:
        self._check("users.delete")
        status_id = self._status_id_by_name(entity_type="user", name="Неактивен")
        current = self.users.get(user_id)
        result = self.users.update(
            actor_user_id=self.actor_user["id"],
            user_id=user_id,
            updates={"is_active": 0, "status_id": status_id},
        )
        if result:
            self._log(entity_type="user", entity_id=user_id, action_type="edit", old=current, new=result)
        return self._attach_status_name(entity_type="user", item=result)

    # Pockets
    def create_pocket(self, data: dict[str, Any]) -> dict[str, Any]:
        self._check("pockets.create")
        data = self._normalize_status_payload(entity_type="pocket", payload=data)
        self._validate_pocket_dates(
            date_start_value=self._as_iso_date_or_none(data.get("date_start")),
            date_end_value=self._as_iso_date_or_none(data.get("date_end")),
        )
        result = self.pockets.create(actor_user_id=self.actor_user["id"], data=data)
        if result:
            self._log(entity_type="pocket", entity_id=result["id"], action_type="create", old=None, new=result)
        return self._attach_status_name(entity_type="pocket", item=result)

    def list_pockets(self, *, status: str | None = None) -> list[dict[str, Any]]:
        self._check("pockets.list")
        rows = self.pockets.list(status=status)
        return [self._attach_status_name(entity_type="pocket", item=row) for row in rows]

    def get_pocket(self, pocket_id: int) -> dict[str, Any]:
        self._check("pockets.read")
        return self._attach_status_name(entity_type="pocket", item=self.pockets.get(pocket_id))

    def update_pocket(self, pocket_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        self._check("pockets.update")
        updates = self._normalize_status_payload(entity_type="pocket", payload=updates)
        current = self.pockets.get(pocket_id)
        if not current:
            return {}
        start_value = self._as_iso_date_or_none(
            updates.get("date_start", current.get("date_start"))
        )
        end_value = self._as_iso_date_or_none(
            updates.get("date_end", current.get("date_end"))
        )
        self._validate_pocket_dates(date_start_value=start_value, date_end_value=end_value)
        result = self.pockets.update(actor_user_id=self.actor_user["id"], pocket_id=pocket_id, updates=updates)
        if result:
            action_type = self._action_type_for_update(updates)
            self._log(entity_type="pocket", entity_id=pocket_id, action_type=action_type, old=current, new=result)
        return self._attach_status_name(entity_type="pocket", item=result)

    # Projects
    def create_project(self, data: dict[str, Any]) -> dict[str, Any]:
        self._check("projects.create")
        data = self._normalize_status_payload(entity_type="project", payload=data)
        result = self.projects.create(actor_user_id=self.actor_user["id"], data=data)
        if result:
            self._log(entity_type="project", entity_id=result["id"], action_type="create", old=None, new=result)
        return self._attach_status_name(entity_type="project", item=result)

    def list_projects(self, *, pocket_id: int | None = None, status: str | None = None) -> list[dict[str, Any]]:
        self._check("projects.list")
        rows = self.projects.list(pocket_id=pocket_id, status=status)
        return [self._attach_status_name(entity_type="project", item=row) for row in rows]

    def get_project(self, project_id: int) -> dict[str, Any]:
        self._check("projects.read")
        return self._attach_status_name(entity_type="project", item=self.projects.get(project_id))

    def update_project(self, project_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        self._check("projects.update")
        updates = self._normalize_status_payload(entity_type="project", payload=updates)
        current = self.projects.get(project_id)
        result = self.projects.update(actor_user_id=self.actor_user["id"], project_id=project_id, updates=updates)
        if result:
            action_type = self._action_type_for_update(updates)
            self._log(entity_type="project", entity_id=project_id, action_type=action_type, old=current, new=result)
        return self._attach_status_name(entity_type="project", item=result)

    # Tasks
    def create_task(self, data: dict[str, Any]) -> dict[str, Any]:
        self._check("tasks.create")
        data = self._normalize_status_payload(entity_type="task", payload=data)
        data.setdefault("status", "Создана")
        if data.get("status_id") is None:
            data["status_id"] = self._status_id_by_name(entity_type="task", name=str(data["status"]))
        data.setdefault("date_created", date.today().isoformat())
        data.setdefault("date_start_work", None)
        data.setdefault("date_done", None)
        if data.get("status") != "Создана":
            raise ValueError("New task must start with status 'Создана'")
        result = self.tasks.create(actor_user_id=self.actor_user["id"], data=data)
        if result:
            self._log(entity_type="task", entity_id=result["id"], action_type="create", old=None, new=result)
        return self._attach_status_name(entity_type="task", item=result)

    def list_tasks(self, *, project_id: int | None = None, status: str | None = None, executor_user_id: int | None = None) -> list[dict[str, Any]]:
        self._check("tasks.list")
        rows = self.tasks.list(project_id=project_id, status=status, executor_user_id=executor_user_id)
        return [self._attach_status_name(entity_type="task", item=row) for row in rows]

    def get_task(self, task_id: int) -> dict[str, Any]:
        self._check("tasks.read")
        return self._attach_status_name(entity_type="task", item=self.tasks.get(task_id))

    def update_task(self, task_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        self._check("tasks.update")
        updates = self._normalize_status_payload(entity_type="task", payload=updates)
        current = self.tasks.get(task_id)
        if not current:
            return {}
        if "status" in updates:
            self._validate_task_status_update(current.get("status"), updates["status"])
        result = self.tasks.update(actor_user_id=self.actor_user["id"], task_id=task_id, updates=updates)
        if result:
            action_type = self._action_type_for_update(updates)
            self._log(entity_type="task", entity_id=task_id, action_type=action_type, old=current, new=result)
        return self._attach_status_name(entity_type="task", item=result)

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

    def list_task_pauses(self, task_id: int | None = None) -> list[dict[str, Any]]:
        self._check("task_pauses.list")
        return self.task_pauses.list(task_id=task_id)

    def get_task_pause(self, pause_id: int) -> dict[str, Any]:
        self._check("task_pauses.read")
        return self.task_pauses.get(pause_id)

    # Logs
    def list_action_log(self, *, entity_type: str | None = None, entity_id: int | None = None) -> list[dict[str, Any]]:
        self._check("action_log.list")
        return self.action_log.list(entity_type=entity_type, entity_id=entity_id)

    def get_action_log(self, log_id: int) -> dict[str, Any]:
        self._check("action_log.read")
        return self.action_log.get(log_id)

    # Task status actions
    def start_task(self, task_id: int, *, comment: str | None = None) -> dict[str, Any]:
        self._check("tasks.update")
        current = self.tasks.get(task_id)
        if not current:
            return {}
        self._validate_task_status_update(current.get("status"), "В работе")
        updates = {"status": "В работе"}
        updates["status_id"] = self._status_id_by_name(entity_type="task", name="В работе")
        if not current.get("date_start_work"):
            updates["date_start_work"] = date.today().isoformat()
        result = self.tasks.update(actor_user_id=self.actor_user["id"], task_id=task_id, updates=updates)
        if result:
            self._log(entity_type="task", entity_id=task_id, action_type="update_status", old=current, new=result, comment=comment)
        return self._attach_status_name(entity_type="task", item=result)

    def pause_task(self, task_id: int, *, comment: str | None = None) -> dict[str, Any]:
        self._check("tasks.update")
        self._check("task_pauses.create")
        current = self.tasks.get(task_id)
        if not current:
            return {}
        self._validate_task_status_update(current.get("status"), "Приостановлена")
        pause_data = {
            "task_id": task_id,
            "date_start": date.today().isoformat(),
            "date_end": None,
        }
        self.task_pauses.create(actor_user_id=self.actor_user["id"], data=pause_data)
        updates = {"status": "Приостановлена"}
        updates["status_id"] = self._status_id_by_name(entity_type="task", name="Приостановлена")
        result = self.tasks.update(actor_user_id=self.actor_user["id"], task_id=task_id, updates=updates)
        if result:
            self._log(entity_type="task", entity_id=task_id, action_type="pause_start", old=current, new=result, comment=comment)
        return self._attach_status_name(entity_type="task", item=result)

    def resume_task(self, task_id: int, *, comment: str | None = None) -> dict[str, Any]:
        self._check("tasks.update")
        self._check("task_pauses.create")
        current = self.tasks.get(task_id)
        if not current:
            return {}
        self._validate_task_status_update(current.get("status"), "В работе")
        pause = self.task_pauses.get_open_pause(task_id)
        if not pause:
            raise ValueError("No active pause for task")
        self.task_pauses.update(
            actor_user_id=self.actor_user["id"],
            pause_id=pause["id"],
            updates={"date_end": date.today().isoformat()},
        )
        updates = {"status": "В работе", "status_id": self._status_id_by_name(entity_type="task", name="В работе")}
        result = self.tasks.update(actor_user_id=self.actor_user["id"], task_id=task_id, updates=updates)
        if result:
            self._log(entity_type="task", entity_id=task_id, action_type="pause_end", old=current, new=result, comment=comment)
        return self._attach_status_name(entity_type="task", item=result)

    def complete_task(self, task_id: int, *, comment: str | None = None) -> dict[str, Any]:
        self._check("tasks.update")
        current = self.tasks.get(task_id)
        if not current:
            return {}
        self._validate_task_status_update(current.get("status"), "Завершена")
        updates = {
            "status": "Завершена",
            "status_id": self._status_id_by_name(entity_type="task", name="Завершена"),
            "date_done": date.today().isoformat(),
        }
        result = self.tasks.update(actor_user_id=self.actor_user["id"], task_id=task_id, updates=updates)
        if result:
            self._log(entity_type="task", entity_id=task_id, action_type="close", old=current, new=result, comment=comment)
        return self._attach_status_name(entity_type="task", item=result)

    # Statuses
    def create_status(self, data: dict[str, Any]) -> dict[str, Any]:
        self._check("users.update")
        result = self.statuses.create(actor_user_id=self.actor_user["id"], data=data)
        if result:
            self._log(entity_type="user", entity_id=self.actor_user["id"], action_type="edit", old=None, new=result)
        return result

    def list_statuses(self, *, entity_type: str | None = None, is_active: int | None = None) -> list[dict[str, Any]]:
        self._check("users.list")
        return self.statuses.list(entity_type=entity_type, is_active=is_active)

    def get_status(self, status_id: int) -> dict[str, Any]:
        self._check("users.list")
        return self.statuses.get(status_id)

    def update_status(self, status_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        self._check("users.update")
        current = self.statuses.get(status_id)
        result = self.statuses.update(actor_user_id=self.actor_user["id"], status_id=status_id, updates=updates)
        if result:
            self._log(entity_type="user", entity_id=self.actor_user["id"], action_type="edit", old=current, new=result)
        return result

    def _status_is_used(self, status_id: int) -> bool:
        checks = [
            ("SELECT 1 FROM users WHERE status_id = ? LIMIT 1",),
            ("SELECT 1 FROM pockets WHERE status_id = ? LIMIT 1",),
            ("SELECT 1 FROM projects WHERE status_id = ? LIMIT 1",),
            ("SELECT 1 FROM tasks WHERE status_id = ? LIMIT 1",),
        ]
        for (query,) in checks:
            if self.conn.execute(query, (status_id,)).fetchone():
                return True
        return False

    def delete_status(self, status_id: int) -> bool:
        self._check("users.update")
        current = self.statuses.get(status_id)
        if not current:
            return False
        if int(current.get("is_system", 0)) == 1:
            raise ValueError("System status cannot be deleted")
        if self._status_is_used(status_id):
            raise ValueError("Status is used and cannot be deleted")
        ok = self.statuses.delete(actor_user_id=self.actor_user["id"], status_id=status_id)
        if ok:
            self._log(entity_type="user", entity_id=self.actor_user["id"], action_type="edit", old=current, new=None)
        return ok

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
