"""FastAPI application for PocketFlow."""
from __future__ import annotations

from fastapi import FastAPI

from backend.db import init_db
from backend.http.routes_action_log import router as action_log_router
from backend.http.routes_pockets import router as pockets_router
from backend.http.routes_projects import router as projects_router
from backend.http.routes_session import router as session_router
from backend.http.routes_statuses import router as statuses_router
from backend.http.routes_task_pauses import router as task_pauses_router
from backend.http.routes_tasks import router as tasks_router
from backend.http.routes_users import router as users_router


def create_app() -> FastAPI:
    app = FastAPI(title="PocketFlow API")

    @app.on_event("startup")
    def _init_db() -> None:
        init_db()

    @app.get("/")
    def root() -> dict[str, str]:
        return {"message": "PocketFlow API"}

    app.include_router(users_router)
    app.include_router(session_router)
    app.include_router(statuses_router)
    app.include_router(pockets_router)
    app.include_router(projects_router)
    app.include_router(tasks_router)
    app.include_router(task_pauses_router)
    app.include_router(action_log_router)

    return app


app = create_app()
