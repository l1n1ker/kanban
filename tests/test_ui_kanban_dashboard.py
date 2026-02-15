from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import ui_tk.main as ui_main


def _new_app() -> ui_main.KanbanTkApp:
    app = ui_main.KanbanTkApp.__new__(ui_main.KanbanTkApp)
    app.selected_project_id = None
    app.theme_tokens = {"icons": {"palette": "light"}}
    return app


def test_dashboard_top_filters_project_fields_only() -> None:
    app = _new_app()
    rows = [
        {"project_id": 1, "project_name": "Alpha", "status": "???????"},
        {"project_id": 2, "project_name": "Beta", "status": "???????"},
    ]
    conds = [ui_main.FilterRowState(logic="AND", field="project_name", op="contains", value="Alp")]
    result = app._apply_project_table_filters(rows, conds)
    assert [r["project_id"] for r in result] == [1]


def test_dashboard_top_ignores_task_only_fields() -> None:
    app = _new_app()
    rows = [
        {"project_id": 1, "project_name": "Alpha", "status": "???????"},
        {"project_id": 2, "project_name": "Beta", "status": "???????"},
    ]
    conds = [ui_main.FilterRowState(logic="AND", field="executor_full_name", op="contains", value="Ivan")]
    result = app._apply_project_table_filters(rows, conds)
    assert [r["project_id"] for r in result] == [1, 2]


def test_selected_project_invalid_after_filter_resets() -> None:
    app = _new_app()
    app.selected_project_id = 2
    app._reconcile_selected_project([{"project_id": 1, "project_name": "Alpha"}])
    assert app.selected_project_id is None


def test_dashboard_on_top_select_does_not_reenter_full_filter() -> None:
    app = _new_app()
    app._in_filter_refresh = False
    app._suppress_top_select_event = False

    class FakeTree:
        @staticmethod
        def selection() -> tuple[str]:
            return ("5",)

    app.top_tree = FakeTree()
    calls = {"bottom": 0, "kanban": 0, "apply": 0, "ind": 0}
    app._refresh_dashboard_bottom_table_from_selection_and_filter = lambda: calls.__setitem__("bottom", calls["bottom"] + 1)
    app._refresh_kanban_board = lambda: calls.__setitem__("kanban", calls["kanban"] + 1)
    app._refresh_global_filter_indicators = lambda: calls.__setitem__("ind", calls["ind"] + 1)
    app._apply_filters = lambda: calls.__setitem__("apply", calls["apply"] + 1)
    app._on_top_select(None)
    assert app.selected_project_id == 5
    assert calls["bottom"] == 1
    assert calls["kanban"] == 1
    assert calls["ind"] == 1
    assert calls["apply"] == 0


def test_project_selection_adds_system_project_filter() -> None:
    app = _new_app()
    app.global_filter_context = ui_main.FilterContext(rows=[ui_main.FilterRowState(field="status", op="!=", value="?????????")])
    app.selected_project_id = 7
    rows = app._build_effective_filter_rows()
    assert any(r.field == "project_id" and r.op == "==" and r.value == "7" and r.tag == "selected" for r in rows)


def test_dashboard_filter_rebuilds_top_then_bottom_once() -> None:
    app = _new_app()
    app._in_filter_refresh = False
    app.filter_rows = []
    app.filter_visible = False
    app.kanban_presets = {}
    app.global_filter_context = ui_main.FilterContext(rows=[])
    app.preset_var = type("DummyVar", (), {"get": lambda self: ui_main.DEFAULT_PRESET_NAME})()
    app.kanban_preset_var = type("DummyVar", (), {"set": lambda self, _v: None})()
    calls = {"top": 0, "bottom": 0, "kanban": 0, "ind": 0}
    app._sync_global_filter_context_from_rows = lambda *a, **k: None
    app._apply_global_filter_context_to_zone = lambda *a, **k: None
    app._refresh_dashboard_top_table_from_filter_context = lambda: calls.__setitem__("top", calls["top"] + 1)
    app._refresh_dashboard_bottom_table_from_selection_and_filter = lambda: calls.__setitem__("bottom", calls["bottom"] + 1)
    app._refresh_kanban_board = lambda: calls.__setitem__("kanban", calls["kanban"] + 1)
    app._refresh_global_filter_indicators = lambda: calls.__setitem__("ind", calls["ind"] + 1)
    app._apply_filters()
    assert calls["top"] == 1
    assert calls["bottom"] == 1
    assert calls["kanban"] == 1
    assert calls["ind"] == 1
    assert app._in_filter_refresh is False


def test_kanban_png_loader_loads_theme_set() -> None:
    app = _new_app()
    paths = app._resolve_kanban_icon_paths("forest-light")
    assert set(paths.keys()) == {"claim", "assign", "start", "pause", "resume", "complete"}
    for path in paths.values():
        assert Path(path).exists()


def test_kanban_png_loader_missing_asset_raises_ui_error(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _new_app()
    monkeypatch.setattr(ui_main, "KANBAN_ACTION_ICONS", {"missing": "missing"})
    with pytest.raises(FileNotFoundError):
        app._resolve_kanban_icon_paths("forest-light")


def test_show_empty_projects_toggle() -> None:
    app = _new_app()

    class DummyVar:
        def __init__(self, value: bool) -> None:
            self.value = value

        def get(self) -> bool:
            return self.value

    app.show_projects_without_tasks_var = DummyVar(False)
    app.projects_by_id = {
        1: {"id": 1, "name": "A", "pocket_id": 10, "curator_it_user_id": 1},
        2: {"id": 2, "name": "B", "pocket_id": 10, "curator_it_user_id": 1},
    }
    app.pockets_by_id = {10: {"id": 10, "name": "P", "owner_user_id": 1}}
    app.users_by_id = {1: {"id": 1, "full_name": "User"}}
    app.global_filter_context = ui_main.FilterContext(rows=[])

    base_rows = [{"project_id": 1, "project_name": "A"}]
    assert app._augment_top_rows_with_empty_projects(list(base_rows)) == base_rows

    app.show_projects_without_tasks_var = DummyVar(True)
    augmented = app._augment_top_rows_with_empty_projects(list(base_rows))
    assert {int(r["project_id"]) for r in augmented} == {1, 2}


def test_dashboard_bottom_controls_packed_after_content() -> None:
    src = inspect.getsource(ui_main.KanbanTkApp._build_dashboard)
    assert "content.pack(fill=BOTH, expand=True)" in src
    assert "self.bottom_controls.pack(fill=\"x\")" in src


def test_filter_panel_pack_before_bottom_controls_dashboard() -> None:
    src = inspect.getsource(ui_main.KanbanTkApp._toggle_filter_panel)
    assert "before=self.bottom_controls" in src


def test_kanban_bottom_controls_packed_after_board() -> None:
    src = inspect.getsource(ui_main.KanbanTkApp._build_kanban)
    assert "board.pack(fill=BOTH, expand=True)" in src
    assert "self.kanban_bottom_controls.pack(fill=\"x\")" in src


def test_filter_panel_pack_before_bottom_controls_kanban() -> None:
    src = inspect.getsource(ui_main.KanbanTkApp._toggle_kanban_filter_panel)
    assert "before=self.kanban_bottom_controls" in src


def test_kanban_columns_have_scroll_container() -> None:
    src = inspect.getsource(ui_main.KanbanTkApp._build_kanban)
    assert "self.kanban_column_canvases" in src
    assert "self.kanban_column_windows" in src
    assert "canvas = Canvas(" in src
    assert "ttk.Scrollbar(col, orient=VERTICAL, command=canvas.yview)" in src


def test_context_keeps_shared_rows_but_zone_visibility_separate() -> None:
    app = _new_app()
    app._row_states_from_ui_rows = lambda _rows: [ui_main.FilterRowState(field="status", op="!=", value="Завершена")]
    app._refresh_global_filter_indicators = lambda: None
    app.global_filter_context = ui_main.FilterContext(rows=[])

    app._sync_global_filter_context_from_rows([], zone="dashboard", visible=True, preset_name="P1")
    assert app.global_filter_context.dashboard_visible is True
    assert app.global_filter_context.kanban_visible is False
    assert app.global_filter_context.preset_name == "P1"

    app._sync_global_filter_context_from_rows([], zone="kanban", visible=False, preset_name="P2")
    assert app.global_filter_context.dashboard_visible is True
    assert app.global_filter_context.kanban_visible is False
    assert app.global_filter_context.preset_name == "P2"


def test_dashboard_visibility_does_not_open_kanban_panel() -> None:
    app = _new_app()
    app.filter_rows = []
    app.filter_visible = True
    app.kanban_filter_visible = False
    app.kanban_presets = {}
    app.global_filter_context = ui_main.FilterContext(rows=[], dashboard_visible=True, kanban_visible=False)
    app.preset_var = type("DummyVar", (), {"get": lambda self: ui_main.DEFAULT_PRESET_NAME})()
    app.kanban_preset_var = type("DummyVar", (), {"set": lambda self, _v: None})()
    app._in_filter_refresh = False
    app._row_states_from_ui_rows = lambda _rows: []
    app._refresh_dashboard_top_table_from_filter_context = lambda: None
    app._refresh_dashboard_bottom_table_from_selection_and_filter = lambda: None
    app._refresh_kanban_board = lambda: None
    app._refresh_global_filter_indicators = lambda: None
    app._replace_kanban_filter_rows_from_context = lambda: None
    app._apply_global_filter_context_to_zone = lambda _zone: None

    app._apply_filters()
    assert app.global_filter_context.dashboard_visible is True
    assert app.global_filter_context.kanban_visible is False


def test_kanban_visibility_does_not_open_dashboard_panel() -> None:
    app = _new_app()
    app.kanban_filter_rows = []
    app.filter_visible = False
    app.kanban_filter_visible = True
    app.presets = {}
    app.global_filter_context = ui_main.FilterContext(rows=[], dashboard_visible=False, kanban_visible=True)
    app.preset_var = type("DummyVar", (), {"set": lambda self, _v: None})()
    app.kanban_preset_var = type("DummyVar", (), {"get": lambda self: ui_main.DEFAULT_PRESET_NAME})()
    app._row_states_from_ui_rows = lambda _rows: []
    app._refresh_dashboard_top_table_from_filter_context = lambda: None
    app._refresh_dashboard_bottom_table_from_selection_and_filter = lambda: None
    app._refresh_kanban_board = lambda: None
    app._apply_global_filter_context_to_zone = lambda _zone: None
    app._refresh_global_filter_indicators = lambda: None

    app._apply_kanban_filters()
    assert app.global_filter_context.dashboard_visible is False
    assert app.global_filter_context.kanban_visible is True


def test_kanban_card_actions_do_not_toggle_kanban_filter_panel() -> None:
    app = _new_app()
    app.kanban_filter_visible = False
    app.global_filter_context = ui_main.FilterContext(rows=[], dashboard_visible=False, kanban_visible=False)
    app.api = type("Api", (), {"task_action": lambda *_a, **_k: None})()
    app._load_dashboard_data = lambda: None
    app._refresh_kanban_board = lambda: None

    app._kanban_task_action(1, "start")
    assert app.kanban_filter_visible is False
    assert app.global_filter_context.kanban_visible is False
