"""Session/introspection HTTP routes."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from backend.http.common import get_actor_user

router = APIRouter(prefix="/session", tags=["session"])


@router.get("/me")
def get_session_me(actor_user: dict[str, Any] = Depends(get_actor_user)) -> dict[str, Any]:
    return {
        "id": int(actor_user["id"]),
        "login": actor_user.get("login", ""),
        "full_name": actor_user.get("full_name", ""),
        "role": actor_user["role"],
    }
