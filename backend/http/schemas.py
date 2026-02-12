"""Pydantic schemas for the HTTP layer."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel


class UserCreate(BaseModel):
    login: str
    full_name: str
    role: Literal["admin", "head", "teamlead", "curator", "executor"]
    is_active: bool = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[Literal["admin", "head", "teamlead", "curator", "executor"]] = None
    is_active: Optional[bool] = None


class UserOut(BaseModel):
    id: int
    login: str
    full_name: str
    role: Literal["admin", "head", "teamlead", "curator", "executor"]
    is_active: bool


class PocketCreate(BaseModel):
    name: str
    date_start: date
    date_end: Optional[date] = None
    status: Literal["Запущен", "Завершён"]
    owner_user_id: int
    department: str


class PocketUpdate(BaseModel):
    name: Optional[str] = None
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    status: Optional[Literal["Запущен", "Завершён"]] = None
    owner_user_id: Optional[int] = None
    department: Optional[str] = None


class PocketOut(BaseModel):
    id: int
    name: str
    date_start: date
    date_end: Optional[date]
    status: Literal["Запущен", "Завершён"]
    owner_user_id: int
    department: str


class ProjectCreate(BaseModel):
    name: str
    pocket_id: int
    status: Literal["Активен", "Завершён"]
    date_start: date
    date_end: Optional[date] = None
    curator_business_user_id: int
    curator_it_user_id: int


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    pocket_id: Optional[int] = None
    status: Optional[Literal["Активен", "Завершён"]] = None
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    curator_business_user_id: Optional[int] = None
    curator_it_user_id: Optional[int] = None


class ProjectOut(BaseModel):
    id: int
    name: str
    pocket_id: int
    status: Literal["Активен", "Завершён"]
    date_start: date
    date_end: Optional[date]
    curator_business_user_id: int
    curator_it_user_id: int


class TaskCreate(BaseModel):
    project_id: int
    description: str
    customer: str
    executor_user_id: int
    code_link: Optional[str] = None


class TaskUpdate(BaseModel):
    description: Optional[str] = None
    customer: Optional[str] = None
    executor_user_id: Optional[int] = None
    code_link: Optional[str] = None


class TaskOut(BaseModel):
    id: int
    project_id: int
    description: str
    status: Literal["Создана", "В работе", "Приостановлена", "Завершена"]
    date_created: date
    date_start_work: Optional[date]
    date_done: Optional[date]
    executor_user_id: int
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
