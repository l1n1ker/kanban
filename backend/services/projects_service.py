"""Project domain service methods."""
from __future__ import annotations

from .common import ServicesCommonMixin


class ProjectsServiceMixin(ServicesCommonMixin):
    def create_project(self, data: dict[str, object]) -> dict[str, object]:
        self._check("projects.create")
        payload = self._normalize_status_payload(entity_type="project", payload=data)
        if payload.get("status_id") is None:
            payload["status_id"] = self._status_id_by_name(entity_type="project", name="Активен")
        if payload.get("status_id") is None:
            raise ValueError("Project status is required")
        payload = self._drop_compat_status_field(payload)
        self._ensure_curator_can_manage_pocket(int(payload["pocket_id"]))
        result = self.projects.create(actor_user_id=self.actor_user["id"], data=payload)
        if result:
            self._log(entity_type="project", entity_id=result["id"], action_type="create", old=None, new=result)
        return self._attach_status_name(entity_type="project", item=result)

    def list_projects(self, *, pocket_id: int | None = None, status: str | None = None) -> list[dict[str, object]]:
        self._check("projects.list")
        status_id = self._status_id_by_name(entity_type="project", name=status) if status else None
        rows = self.projects.list(pocket_id=pocket_id, status_id=status_id)
        return [self._attach_status_name(entity_type="project", item=row) for row in rows]

    def get_project(self, project_id: int) -> dict[str, object]:
        self._check("projects.read")
        return self._attach_status_name(entity_type="project", item=self.projects.get(project_id))

    def update_project(self, project_id: int, updates: dict[str, object]) -> dict[str, object]:
        self._check("projects.update")
        self._ensure_curator_can_manage_project(project_id)
        payload = self._normalize_status_payload(entity_type="project", payload=updates)
        payload = self._drop_compat_status_field(payload)
        if self._is_curator() and "pocket_id" in payload:
            self._ensure_curator_can_manage_pocket(int(payload["pocket_id"]))
        current = self.projects.get(project_id)
        result = self.projects.update(actor_user_id=self.actor_user["id"], project_id=project_id, updates=payload)
        if result:
            self._log(
                entity_type="project",
                entity_id=project_id,
                action_type=self._action_type_for_update(payload),
                old=current,
                new=result,
            )
        return self._attach_status_name(entity_type="project", item=result)
