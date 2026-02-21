"""Pydantic schemas for the HTTP layer."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    login: str
    full_name: str
    role: Literal["admin", "head", "teamlead", "curator", "executor"]
    is_active: bool = True
    status_id: Optional[int] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[Literal["admin", "head", "teamlead", "curator", "executor"]] = None
    is_active: Optional[bool] = None
    status_id: Optional[int] = None


class UserOut(BaseModel):
    id: int
    login: str
    full_name: str
    role: Literal["admin", "head", "teamlead", "curator", "executor"]
    is_active: bool
    status_id: Optional[int] = None
    status_name: Optional[str] = None


class PocketCreate(BaseModel):
    name: str
    date_start: date
    date_end: Optional[date] = None
    status: Optional[Literal["Запущен", "Завершён"]] = Field(
        default=None,
        deprecated=True,
        description="Compatibility input for one release. Use status_id.",
    )
    status_id: Optional[int] = None
    owner_user_id: int
    department: str


class PocketUpdate(BaseModel):
    name: Optional[str] = None
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    status: Optional[Literal["Запущен", "Завершён"]] = Field(
        default=None,
        deprecated=True,
        description="Compatibility input for one release. Use status_id.",
    )
    status_id: Optional[int] = None
    owner_user_id: Optional[int] = None
    department: Optional[str] = None


class PocketOut(BaseModel):
    id: int
    name: str
    date_start: date
    date_end: Optional[date]
    status: Literal["Запущен", "Завершён"] = Field(
        deprecated=True,
        description="Derived compatibility field for one release (from status_id).",
    )
    status_id: Optional[int] = None
    status_name: Optional[str] = None
    owner_user_id: int
    department: str


class ProjectCreate(BaseModel):
    name: str
    project_code: Optional[str] = None
    pocket_id: int
    status: Optional[Literal["Активен", "Завершён"]] = Field(
        default=None,
        deprecated=True,
        description="Compatibility input for one release. Use status_id.",
    )
    status_id: Optional[int] = None
    date_start: date
    date_end: Optional[date] = None
    curator_business_user_id: int
    curator_it_user_id: int


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    project_code: Optional[str] = None
    pocket_id: Optional[int] = None
    status: Optional[Literal["Активен", "Завершён"]] = Field(
        default=None,
        deprecated=True,
        description="Compatibility input for one release. Use status_id.",
    )
    status_id: Optional[int] = None
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    curator_business_user_id: Optional[int] = None
    curator_it_user_id: Optional[int] = None


class ProjectOut(BaseModel):
    id: int
    name: str
    project_code: Optional[str]
    pocket_id: int
    status: Literal["Активен", "Завершён"] = Field(
        deprecated=True,
        description="Derived compatibility field for one release (from status_id).",
    )
    status_id: Optional[int] = None
    status_name: Optional[str] = None
    date_start: date
    date_end: Optional[date]
    curator_business_user_id: int
    curator_it_user_id: int


class TaskCreate(BaseModel):
    project_id: int
    description: str
    customer: str
    status_id: Optional[int] = None
    executor_user_id: Optional[int] = None
    code_link: Optional[str] = None


class TaskUpdate(BaseModel):
    project_id: Optional[int] = None
    status_id: Optional[int] = None
    description: Optional[str] = None
    customer: Optional[str] = None
    executor_user_id: Optional[int] = None
    code_link: Optional[str] = None


class TaskOut(BaseModel):
    id: int
    project_id: int
    description: str
    status: Literal["Создана", "В работе", "Приостановлена", "Завершена"] = Field(
        deprecated=True,
        description="Derived compatibility field for one release (from status_id).",
    )
    status_id: Optional[int] = None
    status_name: Optional[str] = None
    date_created: date
    date_start_work: Optional[date]
    date_done: Optional[date]
    executor_user_id: Optional[int]
    customer: str
    code_link: Optional[str]


class TaskPauseCreate(BaseModel):
    task_id: int
    date_start: date
    date_end: Optional[date] = None


class TaskPauseUpdate(BaseModel):
    date_end: Optional[date] = None


class TaskPauseOut(BaseModel):
    id: int
    task_id: int
    date_start: date
    date_end: Optional[date]


class ActionLogOut(BaseModel):
    id: int
    timestamp: datetime
    user_id: int
    entity_type: Literal["pocket", "project", "task", "user"]
    entity_id: int
    action_type: Literal[
        "create",
        "update_status",
        "assign",
        "pause_start",
        "pause_end",
        "close",
        "edit",
    ]
    old_value: Optional[str]
    new_value: Optional[str]
    comment: Optional[str]


class TaskStatusAction(BaseModel):
    comment: Optional[str] = None


class TaskAssignIn(BaseModel):
    executor_user_id: int
    comment: Optional[str] = None


class StatusCreate(BaseModel):
    entity_type: Literal["pocket", "project", "task", "user"]
    code: str
    name: str
    is_active: bool = True
    sort_order: int = 100
    is_system: bool = False


class StatusUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class StatusOut(BaseModel):
    id: int
    entity_type: Literal["pocket", "project", "task", "user"]
    code: str
    name: str
    is_active: bool
    sort_order: int
    is_system: bool
