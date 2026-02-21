"""Analytics view adapter for gradual decomposition."""
from __future__ import annotations

from typing import Any


class AnalyticsView:
    def __init__(self, app: Any) -> None:
        self.app = app

    def render(self) -> None:
        self.app.show_analytics_view()
