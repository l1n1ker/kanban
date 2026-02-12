"""Pocket HTTP routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.http.common import get_services, handle_service_exception, iso_date
from backend.http.schemas import PocketCreate, PocketOut, PocketUpdate
from backend.services import Services

router = APIRouter(prefix="/pockets", tags=["pockets"])


@router.post("", response_model=PocketOut, status_code=status.HTTP_201_CREATED)
def create_pocket(payload: PocketCreate, svc: Services = Depends(get_services)) -> dict:
    try:
        data = payload.model_dump()
        data["date_start"] = iso_date(data["date_start"])
        data["date_end"] = iso_date(data["date_end"])
        return svc.create_pocket(data)
    except Exception as exc:
        handle_service_exception(exc)


@router.get("", response_model=list[PocketOut])
def list_pockets(status_value: str | None = Query(default=None, alias="status"), svc: Services = Depends(get_services)) -> list[dict]:
    try:
        return svc.list_pockets(status=status_value)
    except Exception as exc:
        handle_service_exception(exc)


@router.get("/{pocket_id}", response_model=PocketOut)
def get_pocket(pocket_id: int, svc: Services = Depends(get_services)) -> dict:
    try:
        result = svc.get_pocket(pocket_id)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pocket not found")
        return result
    except Exception as exc:
        handle_service_exception(exc)


@router.patch("/{pocket_id}", response_model=PocketOut)
def update_pocket(pocket_id: int, payload: PocketUpdate, svc: Services = Depends(get_services)) -> dict:
    try:
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
        if "date_start" in updates:
            updates["date_start"] = iso_date(updates["date_start"])
        if "date_end" in updates:
            updates["date_end"] = iso_date(updates["date_end"])
        result = svc.update_pocket(pocket_id, updates)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pocket not found")
        return result
    except Exception as exc:
        handle_service_exception(exc)
