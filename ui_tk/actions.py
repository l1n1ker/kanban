"""UI actions orchestration (initial extraction layer)."""
from __future__ import annotations

from typing import Any


def run_action(handler: Any, *args: Any, **kwargs: Any) -> Any:
    return handler(*args, **kwargs)
