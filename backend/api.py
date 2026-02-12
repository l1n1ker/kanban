"""UI-facing entrypoints (function-based) for integration."""
from __future__ import annotations

from typing import Any

from .db import get_connection, init_db
from .services import Services


def get_services(actor_user: dict[str, Any]) -> Services:
    conn = get_connection()
    return Services(conn, actor_user=actor_user)


# Example functional entrypoints (call from UI layer)

def create_user(actor_user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    svc = get_services(actor_user)
    try:
        result = svc.create_user(**payload)
        svc.conn.commit()
        return result
    finally:
        svc.conn.close()


def list_users(actor_user: dict[str, Any], *, is_active: int | None = None) -> list[dict[str, Any]]:
    svc = get_services(actor_user)
    try:
        return svc.list_users(is_active=is_active)
    finally:
        svc.conn.close()

def get_user(actor_user: dict[str, Any], user_id: int) -> dict[str, Any]:
    svc = get_services(actor_user)
    try:
        return svc.get_user(user_id)
    finally:
        svc.conn.close()

def update_user(actor_user: dict[str, Any], user_id: int, updates: dict[str, Any]) -> dict[str, Any]:
    svc = get_services(actor_user)
    try:
        result = svc.update_user(user_id, updates)
        svc.conn.commit()
        return result
    finally:
        svc.conn.close()

def create_task(actor_user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    svc = get_services(actor_user)
    try:
        result = svc.create_task(payload)
        svc.conn.commit()
        return result
    finally:
        svc.conn.close()


def list_tasks(actor_user: dict[str, Any], *, project_id: int | None = None, status: str | None = None, executor_user_id: int | None = None) -> list[dict[str, Any]]:
    svc = get_services(actor_user)
    try:
        return svc.list_tasks(project_id=project_id, status=status, executor_user_id=executor_user_id)
    finally:
        svc.conn.close()

def update_task(actor_user: dict[str, Any], task_id: int, updates: dict[str, Any]) -> dict[str, Any]:
    svc = get_services(actor_user)
    try:
        result = svc.update_task(task_id, updates)
        svc.conn.commit()
        return result
    finally:
        svc.conn.close()

# Pockets
def create_pocket(actor_user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    svc = get_services(actor_user)
    try:
        result = svc.create_pocket(payload)
        svc.conn.commit()
        return result
    finally:
        svc.conn.close()

def list_pockets(actor_user: dict[str, Any], *, status: str | None = None) -> list[dict[str, Any]]:
    svc = get_services(actor_user)
    try:
        return svc.list_pockets(status=status)
    finally:
        svc.conn.close()

def update_pocket(actor_user: dict[str, Any], pocket_id: int, updates: dict[str, Any]) -> dict[str, Any]:
    svc = get_services(actor_user)
    try:
        result = svc.update_pocket(pocket_id, updates)
        svc.conn.commit()
        return result
    finally:
        svc.conn.close()

# Projects
def create_project(actor_user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    svc = get_services(actor_user)
    try:
        result = svc.create_project(payload)
        svc.conn.commit()
        return result
    finally:
        svc.conn.close()

def list_projects(actor_user: dict[str, Any], *, pocket_id: int | None = None, status: str | None = None) -> list[dict[str, Any]]:
    svc = get_services(actor_user)
    try:
        return svc.list_projects(pocket_id=pocket_id, status=status)
    finally:
        svc.conn.close()

def update_project(actor_user: dict[str, Any], project_id: int, updates: dict[str, Any]) -> dict[str, Any]:
    svc = get_services(actor_user)
    try:
        result = svc.update_project(project_id, updates)
        svc.conn.commit()
        return result
    finally:
        svc.conn.close()

# Task pauses
def add_task_pause(actor_user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    svc = get_services(actor_user)
    try:
        result = svc.add_task_pause(payload)
        svc.conn.commit()
        return result
    finally:
        svc.conn.close()

def end_task_pause(actor_user: dict[str, Any], pause_id: int, updates: dict[str, Any]) -> dict[str, Any]:
    svc = get_services(actor_user)
    try:
        result = svc.end_task_pause(pause_id, updates)
        svc.conn.commit()
        return result
    finally:
        svc.conn.close()

def list_task_pauses(actor_user: dict[str, Any], task_id: int) -> list[dict[str, Any]]:
    svc = get_services(actor_user)
    try:
        return svc.list_task_pauses(task_id)
    finally:
        svc.conn.close()

# Action log
def list_action_log(actor_user: dict[str, Any], *, entity_type: str | None = None, entity_id: int | None = None) -> list[dict[str, Any]]:
    svc = get_services(actor_user)
    try:
        return svc.list_action_log(entity_type=entity_type, entity_id=entity_id)
    finally:
        svc.conn.close()

# WIP
def wip_for_task(actor_user: dict[str, Any], task_id: int) -> int:
    svc = get_services(actor_user)
    try:
        return svc.wip_for_task(task_id)
    finally:
        svc.conn.close()

def wip_for_project(actor_user: dict[str, Any], project_id: int) -> int:
    svc = get_services(actor_user)
    try:
        return svc.wip_for_project(project_id)
    finally:
        svc.conn.close()

def wip_for_pocket(actor_user: dict[str, Any], pocket_id: int) -> int:
    svc = get_services(actor_user)
    try:
        return svc.wip_for_pocket(pocket_id)
    finally:
        svc.conn.close()
