from __future__ import annotations

import sqlite3


def status_id(conn: sqlite3.Connection, *, entity_type: str, name: str) -> int:
    row = conn.execute(
        "SELECT id FROM statuses WHERE entity_type = ? AND name = ? LIMIT 1",
        (entity_type, name),
    ).fetchone()
    assert row is not None
    return int(row["id"])
