"""Project HTTP routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.http.common import get_services, handle_service_exception, iso_date
from backend.http.schemas import ProjectCreate, ProjectOut, ProjectUpdate
from backend.services import Services

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, svc: Services = Depends(get_services)) -> dict:
    try:
        data = payload.model_dump()
        data["date_start"] = iso_date(data["date_start"])
        data["date_end"] = iso_date(data["date_end"])
        return svc.create_project(data)
    except Exception as exc:
        handle_service_exception(exc)


@router.get("", response_model=list[ProjectOut])
def list_projects(
    pocket_id: int | None = Query(default=None),
    status_value: str | None = Query(default=None, alias="status"),
    svc: Services = Depends(get_services),
) -> list[dict]:
    try:
        return svc.list_projects(pocket_id=pocket_id, status=status_value)
    except Exception as exc:
        handle_service_exception(exc)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, svc: Services = Depends(get_services)) -> dict:
    try:
        result = svc.get_project(project_id)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return result
    except Exception as exc:
        handle_service_exception(exc)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, payload: ProjectUpdate, svc: Services = Depends(get_services)) -> dict:
    try:
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
        if "date_start" in updates:
            updates["date_start"] = iso_date(updates["date_start"])
        if "date_end" in updates:
            updates["date_end"] = iso_date(updates["date_end"])
        result = svc.update_project(project_id, updates)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return result
    except Exception as exc:
        handle_service_exception(exc)
