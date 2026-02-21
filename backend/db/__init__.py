"""Database public API."""
from __future__ import annotations

from .connection import get_connection
from .migrations import migrate_projects_add_project_code, migrate_statuses_model, migrate_tasks_executor_nullable
from .schema import create_schema
from .seed import seed_reference_data
from .validators import validate_status_consistency, validate_status_model


def init_db() -> None:
    conn = get_connection()
    create_schema(conn)
    seed_reference_data(conn)
    migrate_tasks_executor_nullable(conn)
    migrate_projects_add_project_code(conn)
    migrate_statuses_model(conn)
    validate_status_consistency(conn)
    validate_status_model(conn)
    conn.commit()
    conn.close()


__all__ = ["get_connection", "init_db"]
