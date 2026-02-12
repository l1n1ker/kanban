"""User HTTP routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.http.common import get_services, handle_service_exception
from backend.http.schemas import UserCreate, UserOut, UserUpdate
from backend.services import Services

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, svc: Services = Depends(get_services)) -> dict:
    try:
        data = payload.model_dump()
        data["is_active"] = int(data["is_active"])
        return svc.create_user(**data)
    except Exception as exc:
        handle_service_exception(exc)


@router.get("", response_model=list[UserOut])
def list_users(
    is_active: bool | None = Query(default=None),
    svc: Services = Depends(get_services),
) -> list[dict]:
    try:
        is_active_value = None if is_active is None else int(is_active)
        return svc.list_users(is_active=is_active_value)
    except Exception as exc:
        handle_service_exception(exc)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, svc: Services = Depends(get_services)) -> dict:
    try:
        result = svc.get_user(user_id)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return result
    except Exception as exc:
        handle_service_exception(exc)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, svc: Services = Depends(get_services)) -> dict:
    try:
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
        if "is_active" in updates:
            updates["is_active"] = int(updates["is_active"])
        result = svc.update_user(user_id, updates)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return result
    except Exception as exc:
        handle_service_exception(exc)
