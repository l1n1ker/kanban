"""Task HTTP routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.http.common import get_services, handle_service_exception
from backend.http.schemas import TaskCreate, TaskOut, TaskStatusAction, TaskUpdate
from backend.services import Services

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, svc: Services = Depends(get_services)) -> dict:
    try:
        data = payload.model_dump()
        return svc.create_task(data)
    except Exception as exc:
        handle_service_exception(exc)


@router.get("", response_model=list[TaskOut])
def list_tasks(
    project_id: int | None = Query(default=None),
    status_value: str | None = Query(default=None, alias="status"),
    executor_user_id: int | None = Query(default=None),
    svc: Services = Depends(get_services),
) -> list[dict]:
    try:
        return svc.list_tasks(project_id=project_id, status=status_value, executor_user_id=executor_user_id)
    except Exception as exc:
        handle_service_exception(exc)


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, svc: Services = Depends(get_services)) -> dict:
    try:
        result = svc.get_task(task_id)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return result
    except Exception as exc:
        handle_service_exception(exc)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, payload: TaskUpdate, svc: Services = Depends(get_services)) -> dict:
    try:
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
        result = svc.update_task(task_id, updates)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return result
    except Exception as exc:
        handle_service_exception(exc)


@router.post("/{task_id}/start", response_model=TaskOut)
def start_task(task_id: int, payload: TaskStatusAction, svc: Services = Depends(get_services)) -> dict:
    try:
        result = svc.start_task(task_id, comment=payload.comment)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return result
    except Exception as exc:
        handle_service_exception(exc)


@router.post("/{task_id}/pause", response_model=TaskOut)
def pause_task(task_id: int, payload: TaskStatusAction, svc: Services = Depends(get_services)) -> dict:
    try:
        result = svc.pause_task(task_id, comment=payload.comment)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return result
    except Exception as exc:
        handle_service_exception(exc)


@router.post("/{task_id}/resume", response_model=TaskOut)
def resume_task(task_id: int, payload: TaskStatusAction, svc: Services = Depends(get_services)) -> dict:
    try:
        result = svc.resume_task(task_id, comment=payload.comment)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return result
    except Exception as exc:
        handle_service_exception(exc)


@router.post("/{task_id}/complete", response_model=TaskOut)
def complete_task(task_id: int, payload: TaskStatusAction, svc: Services = Depends(get_services)) -> dict:
    try:
        result = svc.complete_task(task_id, comment=payload.comment)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return result
    except Exception as exc:
        handle_service_exception(exc)
