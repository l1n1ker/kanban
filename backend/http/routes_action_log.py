"""Action log HTTP routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.http.common import get_services, handle_service_exception
from backend.http.schemas import ActionLogOut
from backend.services import Services

router = APIRouter(prefix="/action_log", tags=["action_log"])


@router.get("", response_model=list[ActionLogOut])
def list_action_log(
    entity_type: str | None = Query(default=None),
    entity_id: int | None = Query(default=None),
    svc: Services = Depends(get_services),
) -> list[dict]:
    try:
        return svc.list_action_log(entity_type=entity_type, entity_id=entity_id)
    except Exception as exc:
        handle_service_exception(exc)


@router.get("/{log_id}", response_model=ActionLogOut)
def get_action_log(log_id: int, svc: Services = Depends(get_services)) -> dict:
    try:
        result = svc.get_action_log(log_id)
        if not result:
            raise HTTPException(status_code=404, detail="Action log entry not found")
        return result
    except Exception as exc:
        handle_service_exception(exc)
