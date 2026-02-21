"""Timeline view adapter for gradual decomposition."""
from __future__ import annotations

from typing import Any


class TimelineView:
    def __init__(self, app: Any) -> None:
        self.app = app

    def render(self) -> None:
        self.app.show_timeline_view()
