from __future__ import annotations


def actor_headers(*, user_id: int, role: str) -> dict[str, str]:
    return {"X-User-Id": str(user_id), "X-User-Role": role}


def login_headers(*, login: str, role: str) -> dict[str, str]:
    return {"X-User-Login": login, "X-User-Role": role}
