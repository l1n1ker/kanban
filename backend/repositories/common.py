"""Common helpers for repository layer."""
from __future__ import annotations

from typing import Any, Iterable

from backend.models import row_to_dict


def build_update_sql(
    *,
    updates: dict[str, Any],
    allowed_fields: set[str],
) -> tuple[str, list[Any]]:
    if not updates:
        raise ValueError("No fields to update")
    unknown = [key for key in updates.keys() if key not in allowed_fields]
    if unknown:
        raise ValueError(f"Unsupported update fields: {', '.join(sorted(unknown))}")
    fields: list[str] = []
    values: list[Any] = []
    for key, value in updates.items():
        fields.append(f"{key} = ?")
        values.append(value)
    return ", ".join(fields), values


def fetch_one(conn: Any, query: str, params: Iterable[Any]) -> dict[str, Any]:
    row = conn.execute(query, tuple(params)).fetchone()
    return row_to_dict(row) if row else {}


def fetch_all(conn: Any, query: str, params: Iterable[Any]) -> list[dict[str, Any]]:
    rows = conn.execute(query, tuple(params)).fetchall()
    return [row_to_dict(r) for r in rows]
