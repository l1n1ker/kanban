"""HTTP client for the local Project Kanban FastAPI backend."""
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

    def _request(self, path: str, query: dict[str, Any] | None = None) -> Any:
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
        req = Request(url, method="GET", headers=headers)
        try:
            with urlopen(req, timeout=10) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload) if payload else None
        except HTTPError as exc:
            if exc.code == 401:
                raise ApiClientError(
                    f"HTTP 401 for {url}. Login '{self.actor_user_login}' is not mapped to an active user."
                ) from exc
            raise ApiClientError(f"HTTP {exc.code} for {url}") from exc
        except URLError as exc:
            raise ApiClientError(f"API unavailable: {exc.reason}") from exc

    def list_users(self) -> list[dict[str, Any]]:
        return self._request("/users")

    def get_session_user(self) -> dict[str, Any]:
        return self._request("/session/me")

    def list_pockets(self) -> list[dict[str, Any]]:
        return self._request("/pockets")

    def list_projects(self) -> list[dict[str, Any]]:
        return self._request("/projects")

    def list_tasks(self) -> list[dict[str, Any]]:
        return self._request("/tasks")
