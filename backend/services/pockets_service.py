"""Pocket domain service methods."""
from __future__ import annotations

from backend.rbac import AccessDenied

from .common import ServicesCommonMixin


class PocketsServiceMixin(ServicesCommonMixin):
    def create_pocket(self, data: dict[str, object]) -> dict[str, object]:
        self._check("pockets.create")
        payload = self._normalize_status_payload(entity_type="pocket", payload=data)
        if payload.get("status_id") is None:
            payload["status_id"] = self._status_id_by_name(entity_type="pocket", name="Запущен")
        if payload.get("status_id") is None:
            raise ValueError("Pocket status is required")
        payload = self._drop_compat_status_field(payload)
        if self._is_curator():
            owner_user_id = int(payload.get("owner_user_id", 0))
            actor_id = int(self.actor_user["id"])
            if owner_user_id and owner_user_id != actor_id:
                raise AccessDenied("Curator can create only own pocket")
            payload["owner_user_id"] = actor_id
        self._validate_pocket_dates(
            date_start_value=self._as_iso_date_or_none(payload.get("date_start")),
            date_end_value=self._as_iso_date_or_none(payload.get("date_end")),
        )
        result = self.pockets.create(actor_user_id=self.actor_user["id"], data=payload)
        if result:
            self._log(entity_type="pocket", entity_id=result["id"], action_type="create", old=None, new=result)
        return self._attach_status_name(entity_type="pocket", item=result)

    def list_pockets(self, *, status: str | None = None) -> list[dict[str, object]]:
        self._check("pockets.list")
        status_id = self._status_id_by_name(entity_type="pocket", name=status) if status else None
        rows = self.pockets.list(status_id=status_id)
        return [self._attach_status_name(entity_type="pocket", item=row) for row in rows]

    def get_pocket(self, pocket_id: int) -> dict[str, object]:
        self._check("pockets.read")
        return self._attach_status_name(entity_type="pocket", item=self.pockets.get(pocket_id))

    def update_pocket(self, pocket_id: int, updates: dict[str, object]) -> dict[str, object]:
        self._check("pockets.update")
        self._ensure_curator_can_manage_pocket(pocket_id)
        payload = self._normalize_status_payload(entity_type="pocket", payload=updates)
        payload = self._drop_compat_status_field(payload)
        if self._is_curator() and "owner_user_id" in payload:
            if int(payload.get("owner_user_id") or 0) != int(self.actor_user["id"]):
                raise AccessDenied("Curator cannot transfer pocket ownership")
        current = self.pockets.get(pocket_id)
        if not current:
            return {}
        start_value = self._as_iso_date_or_none(payload.get("date_start", current.get("date_start")))
        end_value = self._as_iso_date_or_none(payload.get("date_end", current.get("date_end")))
        self._validate_pocket_dates(date_start_value=start_value, date_end_value=end_value)
        result = self.pockets.update(actor_user_id=self.actor_user["id"], pocket_id=pocket_id, updates=payload)
        if result:
            self._log(
                entity_type="pocket",
                entity_id=pocket_id,
                action_type=self._action_type_for_update(payload),
                old=current,
                new=result,
            )
        return self._attach_status_name(entity_type="pocket", item=result)
