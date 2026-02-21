from __future__ import annotations

import inspect
from pathlib import Path
from datetime import date

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
    assert set(paths.keys()) == {"assign", "start", "pause", "resume", "complete"}
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


def test_timeline_interval_fallback_dates() -> None:
    app = _new_app()
    task = {"date_created": "2026-02-01", "date_start_work": None, "date_done": None}
    start, end = app._task_timeline_bounds(task)
    assert start == date(2026, 2, 1)
    assert end >= start


def test_timeline_truncate_description_40_chars() -> None:
    app = _new_app()
    src = "x" * 50
    result = app._truncate_timeline_text(src, 40)
    assert len(result) == 40
    assert result.endswith("...")


def test_teamlead_can_manage_pockets_gate() -> None:
    app = _new_app()
    app.session_user = {"id": 7, "role": "teamlead"}
    assert app._can_manage_pockets() is True


def test_timeline_full_text_cache_by_task_id() -> None:
    app = _new_app()
    app._build_filtered_task_rows = lambda: [{"id": 7, "description": "a" * 60, "status": "Создана"}]
    app._apply_timeline_slice = lambda rows: rows
    app._task_timeline_bounds = lambda _r: (date(2026, 2, 1), date(2026, 2, 2))
    app._timeline_slice_bounds = lambda show_errors=False: (date(2026, 2, 1), date(2026, 2, 28))
    app._draw_timeline_axis = lambda *_a, **_k: 16
    app._draw_timeline_row_grid = lambda **_k: None
    app._draw_timeline_row = lambda *_a, **_k: None
    app._hide_widget_tooltip = lambda *_a, **_k: None
    app._theme_color = lambda *_a, **_k: "#000000"

    class DummyTree:
        def __bool__(self) -> bool:
            return True

        def get_children(self) -> list[str]:
            return []

        def delete(self, *_args: object) -> None:
            return None

        def insert(self, _p: str, _e: str, iid: str, values: tuple[object, ...]) -> None:
            assert iid == "7"
            assert str(values[1]).endswith("...")

    class DummyCanvas:
        def __bool__(self) -> bool:
            return True

        def delete(self, *_args: object) -> None:
            return None

        def create_text(self, *_args: object, **_kwargs: object) -> None:
            return None

        def configure(self, **_kwargs: object) -> None:
            return None

    app.timeline_rows_tree = DummyTree()
    app.timeline_canvas = DummyCanvas()
    app._refresh_timeline()
    assert app.timeline_full_text_by_task_id[7] == "a" * 60


def test_timeline_slice_intersection() -> None:
    app = _new_app()
    assert app._timeline_intersects_slice(date(2026, 2, 5), date(2026, 2, 10), date(2026, 2, 1), date(2026, 2, 7))
    assert not app._timeline_intersects_slice(date(2026, 2, 8), date(2026, 2, 10), date(2026, 2, 1), date(2026, 2, 7))


def test_timeline_axis_marks_monday_only_labels() -> None:
    app = _new_app()
    calls = {"text": 0}

    class DummyCanvas:
        def create_line(self, *_args: object, **_kwargs: object) -> None:
            return None

        def create_text(self, *_args: object, **_kwargs: object) -> None:
            calls["text"] += 1

    app.timeline_canvas = DummyCanvas()
    app._theme_color = lambda *_a, **_k: "#000000"
    start = date(2026, 2, 2)  # Monday
    end = date(2026, 2, 15)
    app._draw_timeline_axis(start, end, 20, 30, 30, 4)
    # Labels: first day + Mondays in range (2 and 9)
    assert calls["text"] == 2


def test_timeline_axis_draws_daily_vertical_lines() -> None:
    app = _new_app()
    calls = {"line": 0}

    class DummyCanvas:
        def create_line(self, *_args: object, **_kwargs: object) -> None:
            calls["line"] += 1

        def create_text(self, *_args: object, **_kwargs: object) -> None:
            return None

    app.timeline_canvas = DummyCanvas()
    app._theme_color = lambda *_a, **_k: "#000000"
    start = date(2026, 2, 1)
    end = date(2026, 2, 3)
    app._draw_timeline_axis(start, end, 20, 30, 30, 1)
    assert calls["line"] == 4


def test_timeline_global_filter_and_slice_intersection() -> None:
    app = _new_app()

    class DummyVar:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    app.timeline_slice_start_var = DummyVar("2026-02-01")
    app.timeline_slice_end_var = DummyVar("2026-02-10")
    rows = [
        {"id": 1, "date_created": "2026-02-02", "date_start_work": "2026-02-03", "date_done": "2026-02-04"},
        {"id": 2, "date_created": "2026-01-01", "date_start_work": "2026-01-02", "date_done": "2026-01-03"},
    ]
    result = app._apply_timeline_slice(rows)
    assert [r["id"] for r in result] == [1]


def test_task_pauses_grouping_by_task_id() -> None:
    app = _new_app()
    grouped = app._group_pauses_by_task_id(
        [
            {"id": 1, "task_id": 10, "date_start": "2026-02-02", "date_end": "2026-02-03"},
            {"id": 2, "task_id": 10, "date_start": "2026-02-04", "date_end": "2026-02-05"},
            {"id": 3, "task_id": 11, "date_start": "2026-02-06", "date_end": "2026-02-06"},
        ]
    )
    assert set(grouped.keys()) == {10, 11}
    assert len(grouped[10]) == 2
    assert len(grouped[11]) == 1


def test_timeline_period_validation() -> None:
    app = _new_app()

    class DummyVar:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    app.timeline_slice_start_var = DummyVar("2026-03-01")
    app.timeline_slice_end_var = DummyVar("2026-02-01")
    assert app._timeline_slice_bounds(show_errors=False) is None


def test_timeline_period_is_post_filter() -> None:
    app = _new_app()
    app._build_filtered_task_rows = lambda: [{"id": 1}, {"id": 2}]
    app._apply_timeline_slice = lambda rows: [r for r in rows if r["id"] == 1]
    captured = {"rows": []}

    class DummyTree:
        def __bool__(self) -> bool:
            return True

        def get_children(self) -> list[str]:
            return []

        def delete(self, *_args: object) -> None:
            return None

        def insert(self, _p: str, _e: str, iid: str, values: tuple[object, ...]) -> None:
            captured["rows"].append((iid, values))

    class DummyCanvas:
        def __bool__(self) -> bool:
            return True

        def delete(self, *_args: object) -> None:
            return None

        def create_text(self, *_args: object, **_kwargs: object) -> None:
            return None

        def configure(self, **_kwargs: object) -> None:
            return None

    app.timeline_rows_tree = DummyTree()
    app.timeline_canvas = DummyCanvas()
    app._task_timeline_bounds = lambda _r: (date(2026, 2, 1), date(2026, 2, 2))
    app._timeline_slice_bounds = lambda show_errors=False: (date(2026, 2, 1), date(2026, 2, 28))
    app._draw_timeline_axis = lambda *_a, **_k: 16
    app._draw_timeline_row_grid = lambda **_k: None
    app._draw_timeline_row = lambda *_a, **_k: None
    app._theme_color = lambda *_a, **_k: "#000000"
    app._refresh_timeline()
    assert len(captured["rows"]) == 1
    assert captured["rows"][0][0] == "1"


def test_timeline_period_does_not_mutate_global_context_rows() -> None:
    app = _new_app()
    app.global_filter_context = ui_main.FilterContext(rows=[ui_main.FilterRowState(field="status", op="!=", value="Завершена")])
    before = [(r.field, r.op, r.value) for r in app.global_filter_context.rows]
    app._timeline_slice_bounds = lambda show_errors=True: (date(2026, 2, 1), date(2026, 2, 28))
    app._refresh_timeline = lambda: None
    app._apply_timeline_period()
    after = [(r.field, r.op, r.value) for r in app.global_filter_context.rows]
    assert before == after


def test_dashboard_kanban_unaffected_by_timeline_period() -> None:
    app = _new_app()
    calls = {"filters": 0, "kanban": 0, "timeline": 0}
    app._apply_filters = lambda: calls.__setitem__("filters", calls["filters"] + 1)
    app._refresh_kanban_board = lambda: calls.__setitem__("kanban", calls["kanban"] + 1)
    app._refresh_timeline = lambda: calls.__setitem__("timeline", calls["timeline"] + 1)
    app._timeline_slice_bounds = lambda show_errors=True: (date(2026, 2, 1), date(2026, 2, 28))
    app._apply_timeline_period()
    assert calls["timeline"] == 1
    assert calls["filters"] == 0
    assert calls["kanban"] == 0


def test_timeline_filter_panel_controls_present() -> None:
    src = inspect.getsource(ui_main.KanbanTkApp._build_timeline_filter_panel)
    assert "timeline_preset_combo" in src
    assert "_save_current_timeline_preset" in src
    assert "_rename_timeline_preset" in src
    assert "_add_timeline_filter_row" in src


def test_timeline_labels_do_not_contain_question_placeholders() -> None:
    src = inspect.getsource(ui_main.KanbanTkApp._build_timeline)
    assert "????" not in src


def test_timeline_row_alignment_formula_stable() -> None:
    src = inspect.getsource(ui_main.KanbanTkApp._draw_timeline_row)
    assert "y = top_pad + idx * row_h" in src


def test_timeline_split_ratio_persisted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = _new_app()
    cfg = tmp_path / "ui_config.json"
    monkeypatch.setattr(ui_main, "_ui_config_file", lambda: str(cfg))
    app._save_timeline_split_ratio(0.42)
    loaded = app._load_timeline_split_ratio()
    assert loaded == pytest.approx(0.42)
