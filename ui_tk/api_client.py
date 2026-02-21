"""HTTP client for the local PocketFlow FastAPI backend."""
from __future__ import annotations

import json
import getpass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ApiClientError(RuntimeError):
    """Raised when API request fails."""


class ApiClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        actor_user_id: int = 1,
        actor_user_role: str = "admin",
        actor_user_login: str | None = None,
    ) -> None:
        normalized = base_url.strip()
        if "://" not in normalized:
            normalized = f"http://{normalized}"
        if normalized.startswith("http://0.0.0.0:"):
            normalized = normalized.replace("http://0.0.0.0:", "http://127.0.0.1:", 1)
        if normalized.startswith("https://0.0.0.0:"):
            normalized = normalized.replace("https://0.0.0.0:", "https://127.0.0.1:", 1)
        self.base_url = normalized.rstrip("/")
        self.actor_user_id = int(actor_user_id)
        self.actor_user_role = actor_user_role
        self.actor_user_login = (actor_user_login or getpass.getuser()).strip()

    def _request(
        self,
        path: str,
        *,
        method: str = "GET",
        query: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        if query:
            filtered = {k: v for k, v in query.items() if v is not None}
            if filtered:
                url = f"{url}?{urlencode(filtered)}"
        headers = {}
        if self.actor_user_login:
            headers["X-User-Login"] = self.actor_user_login
        else:
            headers["X-User-Id"] = str(self.actor_user_id)
            headers["X-User-Role"] = self.actor_user_role
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = Request(url, method=method, headers=headers, data=data)
        try:
            with urlopen(req, timeout=10) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload) if payload else None
        except HTTPError as exc:
            detail = ""
            try:
                body = exc.read().decode("utf-8")
                if body:
                    detail = f": {body}"
            except Exception:
                detail = ""
            if exc.code == 401:
                raise ApiClientError(
                    f"HTTP 401 for {url}. Login '{self.actor_user_login}' is not mapped to an active user.{detail}"
                ) from exc
            raise ApiClientError(f"HTTP {exc.code} for {url}{detail}") from exc
        except URLError as exc:
            raise ApiClientError(f"API unavailable: {exc.reason}") from exc

    def list_users(self) -> list[dict[str, Any]]:
        return self._request("/users")

    def create_user(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("/users", method="POST", payload=payload)

    def update_user(self, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request(f"/users/{user_id}", method="PATCH", payload=payload)

    def deactivate_user(self, user_id: int) -> dict[str, Any]:
        return self._request(f"/users/{user_id}", method="DELETE")

    def get_session_user(self) -> dict[str, Any]:
        return self._request("/session/me")

    def list_statuses(self, entity_type: str | None = None, is_active: bool | None = None) -> list[dict[str, Any]]:
        return self._request("/statuses", query={"entity_type": entity_type, "is_active": is_active})

    def create_status(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("/statuses", method="POST", payload=payload)

    def update_status(self, status_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request(f"/statuses/{status_id}", method="PATCH", payload=payload)

    def delete_status(self, status_id: int) -> None:
        self._request(f"/statuses/{status_id}", method="DELETE")

    def list_pockets(self, status: str | None = None) -> list[dict[str, Any]]:
        return self._request("/pockets", query={"status": status})

    def create_pocket(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("/pockets", method="POST", payload=payload)

    def update_pocket(self, pocket_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request(f"/pockets/{pocket_id}", method="PATCH", payload=payload)

    def list_projects(self, pocket_id: int | None = None, status: str | None = None) -> list[dict[str, Any]]:
        return self._request("/projects", query={"pocket_id": pocket_id, "status": status})

    def create_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("/projects", method="POST", payload=payload)

    def update_project(self, project_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request(f"/projects/{project_id}", method="PATCH", payload=payload)

    def list_tasks(self) -> list[dict[str, Any]]:
        return self._request("/tasks")

    def list_task_pauses(self, task_id: int | None = None) -> list[dict[str, Any]]:
        return self._request("/task_pauses", query={"task_id": task_id})

    def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("/tasks", method="POST", payload=payload)

    def update_task(self, task_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request(f"/tasks/{task_id}", method="PATCH", payload=payload)

    def task_action(self, task_id: int, action: str, comment: str | None = None) -> dict[str, Any]:
        return self._request(f"/tasks/{task_id}/{action}", method="POST", payload={"comment": comment})

    def claim_task(self, task_id: int, comment: str | None = None) -> dict[str, Any]:
        return self._request(f"/tasks/{task_id}/claim", method="POST", payload={"comment": comment})

    def assign_task(self, task_id: int, executor_user_id: int, comment: str | None = None) -> dict[str, Any]:
        return self._request(
            f"/tasks/{task_id}/assign",
            method="POST",
            payload={"executor_user_id": int(executor_user_id), "comment": comment},
        )
