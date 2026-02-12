"""Task pause HTTP routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.http.common import get_services, handle_service_exception, iso_date
from backend.http.schemas import TaskPauseCreate, TaskPauseOut, TaskPauseUpdate
from backend.services import Services

router = APIRouter(prefix="/task_pauses", tags=["task_pauses"])


@router.post("", response_model=TaskPauseOut, status_code=status.HTTP_201_CREATED)
def create_task_pause(payload: TaskPauseCreate, svc: Services = Depends(get_services)) -> dict:
    try:
        data = payload.model_dump()
        data["date_start"] = iso_date(data["date_start"])
        data["date_end"] = iso_date(data["date_end"])
        return svc.add_task_pause(data)
    except Exception as exc:
        handle_service_exception(exc)


@router.get("", response_model=list[TaskPauseOut])
def list_task_pauses(task_id: int | None = Query(default=None), svc: Services = Depends(get_services)) -> list[dict]:
    try:
        if task_id is None:
            return svc.list_task_pauses()
        return svc.list_task_pauses(task_id)
    except Exception as exc:
        handle_service_exception(exc)


@router.get("/{pause_id}", response_model=TaskPauseOut)
def get_task_pause(pause_id: int, svc: Services = Depends(get_services)) -> dict:
    try:
        result = svc.get_task_pause(pause_id)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task pause not found")
        return result
    except Exception as exc:
        handle_service_exception(exc)


@router.patch("/{pause_id}", response_model=TaskPauseOut)
def update_task_pause(pause_id: int, payload: TaskPauseUpdate, svc: Services = Depends(get_services)) -> dict:
    try:
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
        if "date_end" in updates:
            updates["date_end"] = iso_date(updates["date_end"])
        result = svc.end_task_pause(pause_id, updates)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task pause not found")
        return result
    except Exception as exc:
        handle_service_exception(exc)
