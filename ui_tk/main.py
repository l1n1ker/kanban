"""Compatibility entrypoint for PocketFlow Tkinter UI."""
from __future__ import annotations

from pathlib import Path

# Load full UI implementation into this module namespace to preserve
# compatibility for tests and monkeypatches targeting `ui_tk.main` symbols.
_impl_path = Path(__file__).with_name("app_impl.py")
_impl_source = _impl_path.read_text(encoding="utf-8")
exec(compile(_impl_source, str(_impl_path), "exec"), globals())
