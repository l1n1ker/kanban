from __future__ import annotations

from datetime import date

import ui_tk.main as ui_main


def _new_app() -> ui_main.KanbanTkApp:
    app = ui_main.KanbanTkApp.__new__(ui_main.KanbanTkApp)
    app.selected_project_id = None
    app.timeline_pauses_by_task_id = {}
    return app


def test_analytics_visibility_is_zone_local() -> None:
    app = _new_app()
    app._row_states_from_ui_rows = lambda _rows: []
    app._refresh_global_filter_indicators = lambda: None
    app.global_filter_context = ui_main.FilterContext(rows=[])
    app._sync_global_filter_context_from_rows([], zone="analytics", visible=True, preset_name="P")
    assert app.global_filter_context.analytics_visible is True
    assert app.global_filter_context.dashboard_visible is False
    assert app.global_filter_context.kanban_visible is False


def test_analytics_compute_status_distribution() -> None:
    app = _new_app()
    rows = [
        {"id": 1, "status": "Создана", "date_created": "2026-02-01"},
        {"id": 2, "status": "Создана", "date_created": "2026-02-01"},
        {"id": 3, "status": "В работе", "date_created": "2026-02-01"},
    ]
    data = app._compute_analytics_dataset(rows)
    values = {x["label"]: x["value"] for x in data["status_distribution"]}
    assert values["Создана"] == 2
    assert values["В работе"] == 1


def test_analytics_compute_wip_by_executor() -> None:
    app = _new_app()
    rows = [
        {"id": 1, "status": "Создана", "executor_full_name": "Иван", "date_created": "2026-02-01"},
        {"id": 2, "status": "В работе", "executor_full_name": "Иван", "date_created": "2026-02-01"},
        {"id": 3, "status": "Завершена", "executor_full_name": "Петр", "date_created": "2026-02-01", "date_done": "2026-02-02"},
    ]
    data = app._compute_analytics_dataset(rows)
    values = {x["label"]: x["value"] for x in data["wip_by_executor"]}
    assert values["Иван"] == 2


def test_analytics_compute_throughput_by_week() -> None:
    app = _new_app()
    rows = [
        {"id": 1, "status": "Завершена", "date_created": "2026-02-01", "date_done": "2026-02-10"},
        {"id": 2, "status": "Завершена", "date_created": "2026-02-01", "date_done": "2026-02-11"},
    ]
    data = app._compute_analytics_dataset(rows)
    assert data["throughput_by_week"]
    assert data["throughput_by_week"][0]["value"] == 2


def test_analytics_overdue_detection() -> None:
    app = _new_app()
    rows = [
        {"id": 1, "status": "В работе", "date_created": "2026-01-01", "date_end": "2026-01-05"},
        {"id": 2, "status": "Завершена", "date_created": "2026-01-01", "date_end": "2026-01-05", "date_done": "2026-01-04"},
    ]
    data = app._compute_analytics_dataset(rows)
    assert data["overdue_tasks"][0]["value"] >= 1


def test_analytics_queue_age_only_unassigned_created() -> None:
    app = _new_app()
    rows = [
        {"id": 1, "status": "Создана", "executor_user_id": None, "date_created": "2026-01-01"},
        {"id": 2, "status": "Создана", "executor_user_id": 10, "date_created": "2026-01-01"},
    ]
    data = app._compute_analytics_dataset(rows)
    ids = [item["row_ids"][0] for item in data["queue_age"]]
    assert 1 in ids
    assert 2 not in ids


def test_analytics_drilldown_adds_expected_filter_condition() -> None:
    app = _new_app()
    app.global_filter_context = ui_main.FilterContext(rows=[ui_main.FilterRowState(field="status", op="!=", value="Завершена")])
    app._apply_global_filter_context_to_zone = lambda _zone: None
    app._refresh_dashboard_top_table_from_filter_context = lambda: None
    app._refresh_dashboard_bottom_table_from_selection_and_filter = lambda: None
    app._refresh_kanban_board = lambda: None
    app._refresh_timeline = lambda: None
    app._refresh_analytics = lambda: None
    app._refresh_global_filter_indicators = lambda: None
    app._apply_analytics_drilldown_to_global_filter({"field": "project_id", "op": "==", "value": "5"})
    assert any(r.tag == "analytics_drill" and r.field == "project_id" and r.value == "5" for r in app.global_filter_context.rows)


def test_analytics_clear_drilldown_keeps_user_filters() -> None:
    app = _new_app()
    app.global_filter_context = ui_main.FilterContext(
        rows=[
            ui_main.FilterRowState(field="status", op="!=", value="Завершена"),
            ui_main.FilterRowState(field="project_id", op="==", value="5", tag="analytics_drill"),
        ]
    )
    app._apply_global_filter_context_to_zone = lambda _zone: None
    app._refresh_dashboard_top_table_from_filter_context = lambda: None
    app._refresh_dashboard_bottom_table_from_selection_and_filter = lambda: None
    app._refresh_kanban_board = lambda: None
    app._refresh_timeline = lambda: None
    app._refresh_analytics = lambda: None
    app._refresh_global_filter_indicators = lambda: None
    app._clear_analytics_drilldown()
    assert len(app.global_filter_context.rows) == 1
    assert app.global_filter_context.rows[0].tag == ""


def test_analytics_details_open_task_action() -> None:
    app = _new_app()

    class DummyTree:
        def identify_row(self, _y: int) -> str:
            return "7"

    app.analytics_details_tree = DummyTree()
    app.tasks_all = [{"id": 7, "description": "A"}]
    opened: dict[str, object] = {}
    app._open_task_form = lambda mode, task: opened.update({"mode": mode, "task": task})
    app._on_analytics_details_double_click(type("E", (), {"y": 0})())
    assert opened["mode"] == "edit"
    assert int(opened["task"]["id"]) == 7

