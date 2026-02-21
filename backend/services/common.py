"""Shared service helpers and base context."""
from __future__ import annotations

import sqlite3
from datetime import date
from typing import Any

from backend.logging import format_changes, log_action
from backend.rbac import AccessDenied, check_permission
from backend.repositories import (
    ActionLogRepo,
    PocketsRepo,
    ProjectsRepo,
    StatusesRepo,
    TaskPausesRepo,
    TasksRepo,
    UsersRepo,
)


class ServicesCommonMixin:
    conn: sqlite3.Connection
    actor_user: dict[str, Any]
    users: UsersRepo
    pockets: PocketsRepo
    projects: ProjectsRepo
    tasks: TasksRepo
    task_pauses: TaskPausesRepo
    action_log: ActionLogRepo
    statuses: StatusesRepo
    _valid_task_statuses: set[str]
    _task_transitions: dict[str, set[str]]

    def _init_common(self, conn: sqlite3.Connection, *, actor_user: dict[str, Any]) -> None:
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
        if "status" in updates or "status_id" in updates:
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
            if sid is None:
                raise ValueError(f"Unknown status '{normalized['status']}' for entity_type '{entity_type}'")
            normalized["status_id"] = sid
        return normalized

    def _drop_compat_status_field(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(payload)
        normalized.pop("status", None)
        return normalized

    def _task_status_name(self, item: dict[str, Any]) -> str | None:
        if not item:
            return None
        status_id = item.get("status_id")
        if status_id is not None:
            return self._status_name_by_id(entity_type="task", status_id=int(status_id))
        status_value = item.get("status")
        return str(status_value) if status_value else None

    def _is_curator(self) -> bool:
        return str(self.actor_user.get("role", "")) == "curator"

    def _ensure_curator_can_manage_pocket(self, pocket_id: int) -> None:
        if not self._is_curator():
            return
        pocket = self.pockets.get(pocket_id)
        if not pocket:
            return
        if int(pocket.get("owner_user_id", 0)) != int(self.actor_user["id"]):
            raise AccessDenied("Curator can manage entities only in own pocket")

    def _ensure_curator_can_manage_project(self, project_id: int) -> None:
        if not self._is_curator():
            return
        project = self.projects.get(project_id)
        if not project:
            return
        self._ensure_curator_can_manage_pocket(int(project["pocket_id"]))

    def _ensure_curator_can_manage_task(self, task_id: int) -> None:
        if not self._is_curator():
            return
        task = self.tasks.get(task_id)
        if not task:
            return
        self._ensure_curator_can_manage_project(int(task["project_id"]))

    def _validate_pocket_dates(
        self,
        *,
        date_start_value: str | None,
        date_end_value: str | None,
    ) -> None:
        if not date_start_value or not date_end_value:
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
