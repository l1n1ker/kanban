"""Shared HTTP helpers and dependencies."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterator
import sqlite3

from fastapi import Depends, Header, HTTPException, status

from backend.db import get_connection
from backend.rbac import AccessDenied
from backend.services import Services


def get_actor_user(
    x_user_id: int | None = Header(default=None, alias="X-User-Id"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
    x_user_login: str | None = Header(default=None, alias="X-User-Login"),
) -> dict[str, Any]:
    if x_user_login:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT id, login, full_name, role, is_active FROM users WHERE login = ?",
                (x_user_login,),
            ).fetchone()
        finally:
            conn.close()
        if not row or int(row["is_active"]) != 1:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Login '{x_user_login}' is not mapped to an active user",
            )
        return {
            "id": int(row["id"]),
            "role": row["role"],
            "login": row["login"],
            "full_name": row["full_name"],
        }

    if x_user_id is None or x_user_role is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, login, full_name, role, is_active FROM users WHERE id = ?",
            (x_user_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row or int(row["is_active"]) != 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User id '{x_user_id}' is not active",
        )
    if row["role"] != x_user_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Role mismatch for user id '{x_user_id}'",
        )
    return {
        "id": int(row["id"]),
        "role": row["role"],
        "login": row["login"],
        "full_name": row["full_name"],
    }


def get_services(actor_user: dict[str, Any] = Depends(get_actor_user)) -> Iterator[Services]:
    conn = get_connection()
    svc = Services(conn, actor_user=actor_user)
    try:
        yield svc
        conn.commit()
    finally:
        conn.close()


def handle_service_exception(exc: Exception) -> None:
    if isinstance(exc, AccessDenied):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, ValueError):
        message = str(exc)
        if (
            "transition" in message
            or "active pause" in message
            or "already assigned" in message
            or "cannot claim" in message
            or "Cannot start" in message
            or "assign allowed" in message
        ):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    if isinstance(exc, sqlite3.IntegrityError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Constraint violation")
    raise exc


def iso_date(value: date | None) -> str | None:
    return value.isoformat() if value else None


def iso_datetime(value: datetime | None) -> str | None:
    return value.isoformat(sep=" ") if value else None
