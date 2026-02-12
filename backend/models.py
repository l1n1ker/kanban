"""Data models for core entities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass
class User:
    id: int | None
    login: str
    full_name: str
    role: str
    is_active: int = 1


@dataclass
class Pocket:
    id: int | None
    name: str
    date_start: str
    date_end: str
    status: str
    owner_user_id: int
    department: str


@dataclass
class Project:
    id: int | None
    name: str
    pocket_id: int
    status: str
    date_start: str
    date_end: str
    curator_business_user_id: int
    curator_it_user_id: int


@dataclass
class Task:
    id: int | None
    description: str
    project_id: int
    status: str
    date_created: str
    date_start_work: str | None
    date_done: str | None
    executor_user_id: int
    customer: str | None
    code_link: str | None


@dataclass
class TaskPause:
    id: int | None
    task_id: int
    date_start: str
    date_end: str


@dataclass
class ActionLog:
    id: int | None
    timestamp: str
    user_id: int
    entity_type: str
    entity_id: int
    action_type: str
    old_value: str | None
    new_value: str | None
    comment: str | None


def row_to_dict(row: Mapping[str, Any]) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}
