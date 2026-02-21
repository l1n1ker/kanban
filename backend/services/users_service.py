"""User domain service methods."""
from __future__ import annotations

from typing import Any

from .common import ServicesCommonMixin


class UsersServiceMixin(ServicesCommonMixin):
    def create_user(self, **data: Any) -> dict[str, Any]:
        self._check("users.create")
        data = self._normalize_status_payload(entity_type="user", payload=dict(data))
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
