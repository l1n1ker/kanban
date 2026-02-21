"""Status domain service methods."""
from __future__ import annotations

from .common import ServicesCommonMixin


class StatusesServiceMixin(ServicesCommonMixin):
    def create_status(self, data: dict[str, object]) -> dict[str, object]:
        self._check("users.update")
        result = self.statuses.create(actor_user_id=self.actor_user["id"], data=data)
        if result:
            self._log(entity_type="user", entity_id=self.actor_user["id"], action_type="edit", old=None, new=result)
        return result

    def list_statuses(self, *, entity_type: str | None = None, is_active: int | None = None) -> list[dict[str, object]]:
        self._check("users.list")
        return self.statuses.list(entity_type=entity_type, is_active=is_active)

    def get_status(self, status_id: int) -> dict[str, object]:
        self._check("users.list")
        return self.statuses.get(status_id)

    def update_status(self, status_id: int, updates: dict[str, object]) -> dict[str, object]:
        self._check("users.update")
        current = self.statuses.get(status_id)
        result = self.statuses.update(actor_user_id=self.actor_user["id"], status_id=status_id, updates=updates)
        if result:
            self._log(entity_type="user", entity_id=self.actor_user["id"], action_type="edit", old=current, new=result)
        return result

    def _status_is_used(self, status_id: int) -> bool:
        checks = [
            "SELECT 1 FROM users WHERE status_id = ? LIMIT 1",
            "SELECT 1 FROM pockets WHERE status_id = ? LIMIT 1",
            "SELECT 1 FROM projects WHERE status_id = ? LIMIT 1",
            "SELECT 1 FROM tasks WHERE status_id = ? LIMIT 1",
        ]
        for query in checks:
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
