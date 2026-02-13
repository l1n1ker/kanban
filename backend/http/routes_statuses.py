"""Statuses HTTP routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.http.common import get_services, handle_service_exception
from backend.http.schemas import StatusCreate, StatusOut, StatusUpdate
from backend.services import Services

router = APIRouter(prefix="/statuses", tags=["statuses"])


@router.post("", response_model=StatusOut, status_code=status.HTTP_201_CREATED)
def create_status(payload: StatusCreate, svc: Services = Depends(get_services)) -> dict:
    try:
        data = payload.model_dump()
        data["is_active"] = int(data["is_active"])
        data["is_system"] = int(data["is_system"])
        return svc.create_status(data)
    except Exception as exc:
        handle_service_exception(exc)


@router.get("", response_model=list[StatusOut])
def list_statuses(
    entity_type: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    svc: Services = Depends(get_services),
) -> list[dict]:
    try:
        active_value = None if is_active is None else int(is_active)
        return svc.list_statuses(entity_type=entity_type, is_active=active_value)
    except Exception as exc:
        handle_service_exception(exc)


@router.get("/{status_id}", response_model=StatusOut)
def get_status(status_id: int, svc: Services = Depends(get_services)) -> dict:
    try:
        result = svc.get_status(status_id)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Status not found")
        return result
    except Exception as exc:
        handle_service_exception(exc)


@router.patch("/{status_id}", response_model=StatusOut)
def update_status(status_id: int, payload: StatusUpdate, svc: Services = Depends(get_services)) -> dict:
    try:
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
        if "is_active" in updates:
            updates["is_active"] = int(updates["is_active"])
        result = svc.update_status(status_id, updates)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Status not found")
        return result
    except Exception as exc:
        handle_service_exception(exc)


@router.delete("/{status_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_status(status_id: int, svc: Services = Depends(get_services)) -> None:
    try:
        ok = svc.delete_status(status_id)
        if not ok:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Status not found")
    except Exception as exc:
        handle_service_exception(exc)
