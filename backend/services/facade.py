"""Public services facade."""
from __future__ import annotations

import sqlite3
from typing import Any

from .common import ServicesCommonMixin
from .pockets_service import PocketsServiceMixin
from .projects_service import ProjectsServiceMixin
from .statuses_service import StatusesServiceMixin
from .tasks_service import TasksServiceMixin
from .users_service import UsersServiceMixin


class Services(
    UsersServiceMixin,
    PocketsServiceMixin,
    ProjectsServiceMixin,
    TasksServiceMixin,
    StatusesServiceMixin,
    ServicesCommonMixin,
):
    def __init__(self, conn: sqlite3.Connection, *, actor_user: dict[str, Any]) -> None:
        self._init_common(conn, actor_user=actor_user)
