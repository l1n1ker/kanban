"""SQLite connection helpers."""
from __future__ import annotations

import os
import sqlite3

DB_PATH = os.getenv("KANBAN_DB_PATH", "kanban.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
