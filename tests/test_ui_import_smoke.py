"""Smoke checks for decomposed UI modules importability."""
from __future__ import annotations


def test_ui_module_imports() -> None:
    import ui_tk.actions  # noqa: F401
    import ui_tk.app  # noqa: F401
    import ui_tk.state  # noqa: F401
    import ui_tk.ui.dialogs  # noqa: F401
    import ui_tk.ui.filters  # noqa: F401
    import ui_tk.ui.theme  # noqa: F401
    import ui_tk.views.analytics  # noqa: F401
    import ui_tk.views.dashboard  # noqa: F401
    import ui_tk.views.kanban  # noqa: F401
    import ui_tk.views.shared  # noqa: F401
    import ui_tk.views.timeline  # noqa: F401
    import ui_tk.views.users  # noqa: F401
