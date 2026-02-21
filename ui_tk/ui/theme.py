"""Theme helpers for gradual Tkinter decomposition."""
from __future__ import annotations

from pathlib import Path


def themes_dir(base: Path) -> Path:
    return base / "themes"
