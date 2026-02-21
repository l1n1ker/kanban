"""Centralized role and permission checks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

ROLES = ("admin", "head", "teamlead", "curator", "executor")

ROLE_HIERARCHY = {
    "admin": 5,
    "head": 4,
    "teamlead": 3,
    "curator": 2,
    "executor": 1,
}


def is_at_least(role: str, minimum: str) -> bool:
    return ROLE_HIERARCHY.get(role, 0) >= ROLE_HIERARCHY.get(minimum, 0)


@dataclass(frozen=True)
class Permission:
    action: str
    minimum_role: str | None = None


USER_PERMISSIONS = {
    "users.create": "admin",
    "users.read": "executor",
    "users.update": "admin",
    "users.delete": "admin",
    "users.list": "executor",
}

ENTITY_PERMISSIONS = {
    "pockets.create": "curator",
    "pockets.update": "curator",
    "pockets.delete": "curator",
    "pockets.read": "executor",
    "pockets.list": "executor",
    "projects.create": "curator",
    "projects.update": "curator",
    "projects.delete": "curator",
    "projects.read": "executor",
    "projects.list": "executor",
    "tasks.create": "curator",
    "tasks.update": "curator",
    "tasks.claim": "curator",
    "tasks.delete": "curator",
    "tasks.read": "executor",
    "tasks.list": "executor",
    "task_pauses.create": "curator",
    "task_pauses.read": "executor",
    "task_pauses.list": "executor",
    "action_log.read": "executor",
    "action_log.list": "executor",
}


class AccessDenied(Exception):
    pass


def check_permission(role: str, action: str) -> None:
    if action in USER_PERMISSIONS:
        minimum = USER_PERMISSIONS[action]
        if not is_at_least(role, minimum):
            raise AccessDenied(f"Role '{role}' lacks permission '{action}'")
        return

    if action in ENTITY_PERMISSIONS:
        minimum = ENTITY_PERMISSIONS[action]
        if not is_at_least(role, minimum):
            raise AccessDenied(f"Role '{role}' lacks permission '{action}'")
        return

    raise AccessDenied(f"Unknown permission '{action}'")
