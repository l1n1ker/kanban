"""Task-related service methods and workflow actions."""
from __future__ import annotations

from datetime import date
from typing import Any

from .common import ServicesCommonMixin


class TasksServiceMixin(ServicesCommonMixin):
    def create_task(self, data: dict[str, Any]) -> dict[str, Any]:
        self._check("tasks.create")
        self._ensure_curator_can_manage_project(int(data["project_id"]))
        payload = self._normalize_status_payload(entity_type="task", payload=data)
        requested_status = str(payload.get("status") or "Создана")
        if payload.get("status_id") is None:
            payload["status_id"] = self._status_id_by_name(entity_type="task", name=requested_status)
        payload = self._drop_compat_status_field(payload)
        payload.setdefault("date_created", date.today().isoformat())
        payload.setdefault("date_start_work", None)
        payload.setdefault("date_done", None)
        if payload.get("status_id") is None:
            raise ValueError("Task status is required")
        current_status = self._status_name_by_id(entity_type="task", status_id=int(payload["status_id"]))
        if current_status != "Создана":
            raise ValueError("New task must start with status 'Создана'")
        result = self.tasks.create(actor_user_id=self.actor_user["id"], data=payload)
        if result:
            self._log(entity_type="task", entity_id=result["id"], action_type="create", old=None, new=result)
        return self._attach_status_name(entity_type="task", item=result)

    def list_tasks(
        self,
        *,
        project_id: int | None = None,
        status: str | None = None,
        executor_user_id: int | None = None,
    ) -> list[dict[str, Any]]:
        self._check("tasks.list")
        status_id = self._status_id_by_name(entity_type="task", name=status) if status else None
        rows = self.tasks.list(project_id=project_id, status_id=status_id, executor_user_id=executor_user_id)
        return [self._attach_status_name(entity_type="task", item=row) for row in rows]

    def get_task(self, task_id: int) -> dict[str, Any]:
        self._check("tasks.read")
        return self._attach_status_name(entity_type="task", item=self.tasks.get(task_id))

    def update_task(self, task_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        self._check("tasks.update")
        self._ensure_curator_can_manage_task(task_id)
        payload = self._normalize_status_payload(entity_type="task", payload=updates)
        payload = self._drop_compat_status_field(payload)
        if self._is_curator() and "project_id" in payload:
            self._ensure_curator_can_manage_project(int(payload["project_id"]))
        current = self.tasks.get(task_id)
        if not current:
            return {}
        if "status" in payload:
            current_status = self._task_status_name(current)
            if not current_status:
                raise ValueError("Current task status is not defined")
            self._validate_task_status_update(current_status, str(payload["status"]))
        result = self.tasks.update(actor_user_id=self.actor_user["id"], task_id=task_id, updates=payload)
        if result:
            self._log(
                entity_type="task",
                entity_id=task_id,
                action_type=self._action_type_for_update(payload),
                old=current,
                new=result,
            )
        return self._attach_status_name(entity_type="task", item=result)

    def add_task_pause(self, data: dict[str, Any]) -> dict[str, Any]:
        self._check("task_pauses.create")
        result = self.task_pauses.create(actor_user_id=self.actor_user["id"], data=data)
        if result:
            self._log(entity_type="task", entity_id=int(data["task_id"]), action_type="pause_start", old=None, new=result)
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

    def list_action_log(self, *, entity_type: str | None = None, entity_id: int | None = None) -> list[dict[str, Any]]:
        self._check("action_log.list")
        return self.action_log.list(entity_type=entity_type, entity_id=entity_id)

    def get_action_log(self, log_id: int) -> dict[str, Any]:
        self._check("action_log.read")
        return self.action_log.get(log_id)

    def start_task(self, task_id: int, *, comment: str | None = None) -> dict[str, Any]:
        self._check("tasks.update")
        self._ensure_curator_can_manage_task(task_id)
        current = self.tasks.get(task_id)
        if not current:
            return {}
        if current.get("executor_user_id") is None:
            raise ValueError("Cannot start task without executor")
        current_status = self._task_status_name(current)
        if not current_status:
            raise ValueError("Current task status is not defined")
        self._validate_task_status_update(current_status, "В работе")
        updates: dict[str, Any] = {"status_id": self._status_id_by_name(entity_type="task", name="В работе")}
        if not current.get("date_start_work"):
            updates["date_start_work"] = date.today().isoformat()
        result = self.tasks.update(actor_user_id=self.actor_user["id"], task_id=task_id, updates=updates)
        if result:
            self._log(entity_type="task", entity_id=task_id, action_type="update_status", old=current, new=result, comment=comment)
        return self._attach_status_name(entity_type="task", item=result)

    def pause_task(self, task_id: int, *, comment: str | None = None) -> dict[str, Any]:
        self._check("tasks.update")
        self._check("task_pauses.create")
        self._ensure_curator_can_manage_task(task_id)
        current = self.tasks.get(task_id)
        if not current:
            return {}
        current_status = self._task_status_name(current)
        if not current_status:
            raise ValueError("Current task status is not defined")
        self._validate_task_status_update(current_status, "Приостановлена")
        self.task_pauses.create(
            actor_user_id=self.actor_user["id"],
            data={"task_id": task_id, "date_start": date.today().isoformat(), "date_end": None},
        )
        updates = {"status_id": self._status_id_by_name(entity_type="task", name="Приостановлена")}
        result = self.tasks.update(actor_user_id=self.actor_user["id"], task_id=task_id, updates=updates)
        if result:
            self._log(entity_type="task", entity_id=task_id, action_type="pause_start", old=current, new=result, comment=comment)
        return self._attach_status_name(entity_type="task", item=result)

    def resume_task(self, task_id: int, *, comment: str | None = None) -> dict[str, Any]:
        self._check("tasks.update")
        self._check("task_pauses.create")
        self._ensure_curator_can_manage_task(task_id)
        current = self.tasks.get(task_id)
        if not current:
            return {}
        current_status = self._task_status_name(current)
        if not current_status:
            raise ValueError("Current task status is not defined")
        self._validate_task_status_update(current_status, "В работе")
        pause = self.task_pauses.get_open_pause(task_id)
        if not pause:
            raise ValueError("No active pause for task")
        self.task_pauses.update(
            actor_user_id=self.actor_user["id"],
            pause_id=pause["id"],
            updates={"date_end": date.today().isoformat()},
        )
        updates = {"status_id": self._status_id_by_name(entity_type="task", name="В работе")}
        result = self.tasks.update(actor_user_id=self.actor_user["id"], task_id=task_id, updates=updates)
        if result:
            self._log(entity_type="task", entity_id=task_id, action_type="pause_end", old=current, new=result, comment=comment)
        return self._attach_status_name(entity_type="task", item=result)

    def complete_task(self, task_id: int, *, comment: str | None = None) -> dict[str, Any]:
        self._check("tasks.update")
        self._ensure_curator_can_manage_task(task_id)
        current = self.tasks.get(task_id)
        if not current:
            return {}
        current_status = self._task_status_name(current)
        if not current_status:
            raise ValueError("Current task status is not defined")
        self._validate_task_status_update(current_status, "Завершена")
        updates = {
            "status_id": self._status_id_by_name(entity_type="task", name="Завершена"),
            "date_done": date.today().isoformat(),
        }
        result = self.tasks.update(actor_user_id=self.actor_user["id"], task_id=task_id, updates=updates)
        if result:
            self._log(entity_type="task", entity_id=task_id, action_type="close", old=current, new=result, comment=comment)
        return self._attach_status_name(entity_type="task", item=result)

    def claim_task(self, task_id: int, *, comment: str | None = None) -> dict[str, Any]:
        self._check("tasks.claim")
        self._ensure_curator_can_manage_task(task_id)
        current = self.tasks.get(task_id)
        if not current:
            return {}
        if current.get("executor_user_id") is not None:
            raise ValueError("Task already assigned")
        if self._task_status_name(current) != "Создана":
            raise ValueError("Task cannot claim from current status")

        in_progress_id = self._status_id_by_name(entity_type="task", name="В работе")
        today = date.today().isoformat()
        cur = self.conn.execute(
            """
            UPDATE tasks
            SET executor_user_id = ?, status_id = ?, date_start_work = COALESCE(date_start_work, ?)
            WHERE id = ? AND executor_user_id IS NULL AND status_id = (
                SELECT id FROM statuses WHERE entity_type = 'task' AND name = 'Создана' LIMIT 1
            )
            """,
            (int(self.actor_user["id"]), in_progress_id, today, task_id),
        )
        if cur.rowcount == 0:
            raise ValueError("Task already assigned")
        result = self.tasks.get(task_id)
        self._log(entity_type="task", entity_id=task_id, action_type="assign", old=current, new=result, comment=comment)
        self._log(entity_type="task", entity_id=task_id, action_type="update_status", old=current, new=result, comment=comment)
        return self._attach_status_name(entity_type="task", item=result)

    def assign_task(self, task_id: int, *, executor_user_id: int, comment: str | None = None) -> dict[str, Any]:
        self._check("tasks.update")
        self._ensure_curator_can_manage_task(task_id)
        current = self.tasks.get(task_id)
        if not current:
            return {}
        if self._task_status_name(current) != "Создана":
            raise ValueError("Task assign allowed only from status 'Создана'")
        target = self.users.get(int(executor_user_id))
        if not target:
            raise ValueError("Executor not found")
        if int(target.get("is_active", 0)) != 1:
            raise ValueError("Executor is inactive")
        updates = {"executor_user_id": int(executor_user_id)}
        result = self.tasks.update(actor_user_id=self.actor_user["id"], task_id=task_id, updates=updates)
        if result:
            self._log(entity_type="task", entity_id=task_id, action_type="assign", old=current, new=result, comment=comment)
        return self._attach_status_name(entity_type="task", item=result)

    def wip_for_task(self, task_id: int) -> int:
        task = self.tasks.get(task_id)
        return 1 if task and self._task_status_name(task) == "В работе" else 0

    def wip_for_project(self, project_id: int) -> int:
        in_progress_id = self._status_id_by_name(entity_type="task", name="В работе")
        if in_progress_id is None:
            return 0
        rows = self.conn.execute(
            "SELECT COUNT(*) AS cnt FROM tasks WHERE project_id = ? AND status_id = ?",
            (project_id, in_progress_id),
        ).fetchone()
        return int(rows["cnt"]) if rows else 0

    def wip_for_pocket(self, pocket_id: int) -> int:
        in_progress_id = self._status_id_by_name(entity_type="task", name="В работе")
        if in_progress_id is None:
            return 0
        rows = self.conn.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM tasks t
            JOIN projects p ON p.id = t.project_id
            WHERE p.pocket_id = ? AND t.status_id = ?
            """,
            (pocket_id, in_progress_id),
        ).fetchone()
        return int(rows["cnt"]) if rows else 0
