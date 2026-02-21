"""Action log helpers."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping
import sqlite3


def _format_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, str):
        return value
    return str(value)


def format_changes(old: Mapping[str, Any] | None, new: Mapping[str, Any] | None) -> tuple[str | None, str | None]:
    def to_text(data: Mapping[str, Any] | None) -> str | None:
        if not data:
            return None
        parts = [f"{key}={_format_value(data[key])}" for key in sorted(data.keys())]
        return "; ".join(parts)

    return to_text(old), to_text(new)


def log_action(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    entity_type: str,
    entity_id: int,
    action_type: str,
    old_value: str | None,
    new_value: str | None,
    comment: str | None = None,
) -> None:
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """
        INSERT INTO action_log (timestamp, user_id, entity_type, entity_id, action_type, old_value, new_value, comment)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (timestamp, user_id, entity_type, entity_id, action_type, old_value, new_value, comment),
    )
