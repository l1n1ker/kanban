"""Shared view helpers for incremental split."""
from __future__ import annotations

from typing import Any


def call_view(app: Any, method_name: str) -> None:
    getattr(app, method_name)()
