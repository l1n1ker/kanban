"""Tkinter desktop UI for PocketFlow."""
from __future__ import annotations

import json
import os
import getpass
import csv
from collections import defaultdict
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from statistics import median
from tkinter import BOTH, BOTTOM, END, LEFT, RIGHT, TOP, VERTICAL, BooleanVar, Canvas, PhotoImage, StringVar, Tk, Toplevel
from tkinter import font as tkfont
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any

from ui_tk.api_client import ApiClient, ApiClientError

try:
    from tkcalendar import Calendar
except Exception:
    Calendar = None

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None

try:
    from openpyxl import Workbook
except Exception:
    Workbook = None


DEFAULT_PRESET_NAME = "Активные задачи"
TOP_COLUMN_TITLES: dict[str, str] = {
    "pocket_id": "ID кармана",
    "pocket_name": "Карман",
    "project_id": "ID проекта",
    "project_name": "Проект",
    "project_code": "Код проекта",
    "date_start": "Начало",
    "date_end": "Окончание",
    "status": "Статус",
    "owner": "Ответственный",
    "owner_it": "Ответственный ИТ",
}
BOTTOM_COLUMN_TITLES: dict[str, str] = {
    "id": "ID задачи",
    "description": "Описание",
    "status": "Статус",
    "date_created": "Создана",
    "date_start_work": "Старт работы",
    "date_done": "Завершена",
    "executor_full_name": "Исполнитель",
    "customer": "Заказчик",
    "code_link": "Код/ссылка",
}
POCKET_COLUMN_TITLES: dict[str, str] = {
    "id": "ID",
    "name": "Наименование",
    "status": "Статус",
    "date_start": "Начало",
    "date_end": "Окончание",
    "owner": "Ответственный",
    "department": "Подразделение",
}
PROJECT_COLUMN_TITLES: dict[str, str] = {
    "id": "ID",
    "pocket_id": "ID кармана",
    "pocket_name": "Карман",
    "name": "Наименование",
    "project_code": "Код проекта",
    "status": "Статус",
    "date_start": "Начало",
    "date_end": "Окончание",
    "curator_business": "Куратор бизнес",
    "curator_it": "Куратор ИТ",
}
DEFAULT_THEME_NAME = "forest-light"
DEFAULT_THEME_TOKENS: dict[str, Any] = {
    "id": "forest-light",
    "base_ttk_theme": "forest-light",
    "colors": {
        "surface_bg": "#F7F8F5",
        "surface_panel": "#FFFFFF",
        "text_primary": "#1F2A2A",
        "text_muted": "#5F6B6D",
        "accent": "#4F6B5A",
        "accent_hover": "#3F594A",
        "selection_bg": "#6E8B74",
        "selection_fg": "#FFFFFF",
        "border": "#D8DDD8",
        "danger": "#B5483A",
        "warning": "#B07A2F",
        "info": "#3D6475",
        "success": "#4E7A60",
    },
    "roles": {
        "admin": "#B5483A",
        "head": "#B07A2F",
        "teamlead": "#3D6475",
        "curator": "#4E7A60",
        "executor": "#5F6B6D",
    },
    "icons": {"palette": "light"},
}
PROJECT_FILTER_FIELDS = {
    "pocket_id",
    "pocket_name",
    "project_id",
    "project_name",
    "project_code",
    "date_start",
    "date_end",
    "status",
    "owner",
    "owner_it",
}
KANBAN_ACTION_ICONS = {
    "assign": "assign",
    "start": "start",
    "pause": "pause",
    "resume": "resume",
    "complete": "complete",
}
TIMELINE_ROW_HEIGHT = 30
TIMELINE_DEFAULT_SPLIT_RATIO = 0.38


def _app_dir() -> str:
    base = os.getenv("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "pocketflow")
    os.makedirs(path, exist_ok=True)
    return path


def _preset_file() -> str:
    return os.path.join(_app_dir(), "filter_presets.json")


def _kanban_preset_file() -> str:
    return os.path.join(_app_dir(), "kanban_filter_presets.json")


def _ui_config_file() -> str:
    return os.path.join(_app_dir(), "ui_config.json")


def _themes_dir() -> str:
    return os.path.join(os.path.dirname(__file__), "themes")


def _app_icon_file() -> str:
    return os.path.join(_themes_dir(), "app.ico")


def _app_logo_file() -> str:
    return os.path.join(_themes_dir(), "logo.png")


def _theme_file(theme_id: str) -> str:
    return os.path.join(_themes_dir(), f"{theme_id.replace('-', '_')}.json")


def _icons_source_dir(palette: str) -> str:
    if palette not in {"light", "dark"}:
        palette = "light"
    return os.path.join(os.path.dirname(__file__), "assets", "icons", palette)


def _forest_theme_file(theme_name: str) -> str:
    if theme_name == "forest-light":
        return os.path.join(os.path.dirname(__file__), "vendor", "forest", "forest-light.tcl")
    return os.path.join(os.path.dirname(__file__), "vendor", "forest", "forest-dark.tcl")


@dataclass
class FilterRow:
    frame: ttk.Frame
    logic_var: StringVar
    field_var: StringVar
    op_var: StringVar
    value_var: StringVar


@dataclass
class FilterRowState:
    logic: str = "AND"
    field: str = "status"
    op: str = "!="
    value: str = "Завершена"
    tag: str = ""


@dataclass
class FilterContext:
    rows: list[FilterRowState]
    preset_name: str = DEFAULT_PRESET_NAME
    dashboard_visible: bool = False
    kanban_visible: bool = False
    timeline_visible: bool = False
    analytics_visible: bool = False
    summary_short: str = "Фильтр: пуст"
    summary_full: str = "Фильтр пуст"


class KanbanTkApp(Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("PocketFlow")
        self.geometry("1400x860")
        try:
            self.state("zoomed")
        except Exception:
            try:
                self.attributes("-zoomed", True)
            except Exception:
                pass
        self._window_logo_image: PhotoImage | None = None
        self._about_logo_image: PhotoImage | None = None
        self._apply_window_icon(self)
        self.system_login = (os.getenv("PROJECT_KANBAN_LOGIN") or os.getenv("USERNAME") or getpass.getuser()).strip()
        self.api = ApiClient(actor_user_login=self.system_login)
        self.db_settings = self._load_db_settings()
        self.db_settings_window: Toplevel | None = None
        self.user_guide_window: Toplevel | None = None
        self.session_user: dict[str, Any] | None = None
        self.session_var = StringVar(value=f"Сессия: login={self.system_login}")
        self.theme_name = self._load_theme_name()
        self.theme_tokens = self._load_theme_tokens_with_fallback(self.theme_name)
        self.theme_name = str(self.theme_tokens.get("id", DEFAULT_THEME_NAME))
        self.theme_var = StringVar(value=self.theme_name)
        self.role_colors = self._role_palette_for_theme(self.theme_name)
        self._setup_forest_theme()
        self._apply_theme_settings()

        self.users_by_id: dict[int, dict[str, Any]] = {}
        self.pockets_by_id: dict[int, dict[str, Any]] = {}
        self.projects_by_id: dict[int, dict[str, Any]] = {}
        self.tasks_all: list[dict[str, Any]] = []
        self.selected_project_id: int | None = None
        self.show_projects_without_tasks_var = BooleanVar(value=False)
        self.current_zone = "dashboard"
        self._in_filter_refresh = False
        self._suppress_top_select_event = False

        self.filter_visible = False
        self.filter_rows: list[FilterRow] = []
        self.presets = self._load_presets()
        self.filter_summary_var = StringVar(value="Фильтр: пуст")
        self._filter_summary_full_text = "Фильтр пуст"
        self._filter_tooltip: Toplevel | None = None
        self.kanban_filter_visible = False
        self.kanban_filter_rows: list[FilterRow] = []
        self.kanban_presets = self._load_kanban_presets()
        self.kanban_filter_summary_var = StringVar(value="Фильтр: пуст")
        self._kanban_filter_summary_full_text = "Фильтр пуст"
        self._kanban_filter_tooltip: Toplevel | None = None
        self._widget_tooltip: Toplevel | None = None
        self.timeline_slice_start_var = StringVar(value="")
        self.timeline_slice_end_var = StringVar(value="")
        self.timeline_filter_summary_var = StringVar(value="Фильтр: пуст")
        self.timeline_rows_tree: ttk.Treeview | None = None
        self.timeline_canvas: Canvas | None = None
        self.timeline_pauses_by_task_id: dict[int, list[dict[str, Any]]] = {}
        self.timeline_filter_visible = False
        self.timeline_filter_rows: list[FilterRow] = []
        self.timeline_full_text_by_task_id: dict[int, str] = {}
        self._timeline_hover_task_id: int | None = None
        self.timeline_split_ratio = self._load_timeline_split_ratio()
        self._syncing_timeline_scroll = False
        self.analytics_filter_visible = False
        self.analytics_filter_rows: list[FilterRow] = []
        self.analytics_filter_summary_var = StringVar(value="Фильтр: пуст")
        self.analytics_selected_slice: dict[str, Any] | None = None
        self.analytics_details_tree: ttk.Treeview | None = None
        self.analytics_charts: dict[str, Canvas] = {}
        self.analytics_rows_cache: list[dict[str, Any]] = []
        self.global_filter_context = FilterContext(
            rows=[FilterRowState(logic="AND", field="status", op="!=", value="Завершена")]
        )
        self.icon_images: dict[str, PhotoImage] = {}
        self._icon_error_shown = False
        self.pocket_window: Toplevel | None = None
        self.pocket_tree: ttk.Treeview | None = None
        self.pocket_status_filter_var = StringVar(value="Активные")
        self.pocket_users_by_id: dict[int, dict[str, Any]] = {}
        self.department_catalog: list[str] = []
        self.project_window: Toplevel | None = None
        self.project_tree: ttk.Treeview | None = None
        self.project_status_filter_var = StringVar(value="Активные")
        self.task_window: Toplevel | None = None
        self.task_tree: ttk.Treeview | None = None
        self.task_status_filter_var = StringVar(value="Активные")
        self.tasks_map: dict[int, dict[str, Any]] = {}
        self.users_window: Toplevel | None = None
        self.users_tree: ttk.Treeview | None = None
        self.statuses_window: Toplevel | None = None
        self.statuses_tree: ttk.Treeview | None = None
        self.status_entity_filter_var = StringVar(value="user")

        self._build_menu()
        self._build_ribbon()
        self._build_zones()
        self._sync_global_filter_context_from_rows(
            self.filter_rows,
            zone="dashboard",
            preset_name=self.preset_var.get() if hasattr(self, "preset_var") else DEFAULT_PRESET_NAME,
            visible=self.filter_visible,
        )
        self._apply_global_filter_context_to_zone("kanban")
        self._apply_global_filter_context_to_zone("timeline")
        self._apply_global_filter_context_to_zone("analytics")
        self._show_zone("dashboard")
        self._load_dashboard_data()

    def _build_menu(self) -> None:
        self.menu_bar = ttk.Frame(self, padding=(8, 4))
        self.menu_bar.pack(side=TOP, fill="x")
        self._menu_actions: dict[str, Any] = {
            "Карманы": self._open_pockets_window,
            "Проекты": self._open_projects_window,
            "Задачи": self._open_tasks_window,
            "Пользователи": self._open_users_window,
            "Статусы": self._open_statuses_window,
            "База данных": self._open_db_settings_window,
            "Экспорт": self._open_export_window,
            "Информация о теме": self._show_theme_info,
            "Руководство пользователя": self._open_user_guide_window,
            "О программе": self._show_about,
        }
        self._menu_vars: list[StringVar] = []
        self._mk_vendor_option_menu("Главная", ["Карманы", "Проекты", "Задачи"])
        self._mk_vendor_option_menu("Справочники", ["Пользователи", "Статусы"])
        self._mk_vendor_option_menu("Настройки", ["База данных", "Экспорт", "Информация о теме"])
        self._mk_vendor_option_menu("Помощь", ["Руководство пользователя", "О программе"])

        ttk.Frame(self.menu_bar).pack(side=LEFT, fill="x", expand=True)
        self._mk_button(self.menu_bar, "Аналитика", lambda: self._show_zone("analytics")).pack(side=RIGHT, padx=4)
        self._mk_button(self.menu_bar, "Timeline", lambda: self._show_zone("timeline")).pack(side=RIGHT, padx=4)
        self._mk_button(self.menu_bar, "Kanban", lambda: self._show_zone("kanban")).pack(side=RIGHT, padx=4)
        self._mk_button(self.menu_bar, "Дэшборд", lambda: self._show_zone("dashboard")).pack(side=RIGHT, padx=4)

    def _build_ribbon(self) -> None:
        self.ribbon = ttk.Frame(self, padding=(8, 8))
        self.ribbon.pack(side=TOP, fill="x")
        ttk.Frame(self.ribbon).pack(side=LEFT, fill="x", expand=True)

    def _build_zones(self) -> None:
        self.zones: dict[str, ttk.Frame] = {}
        container = ttk.Frame(self)
        container.pack(fill=BOTH, expand=True)

        dashboard = ttk.Frame(container)
        self._build_dashboard(dashboard)
        self.zones["dashboard"] = dashboard

        kanban = ttk.Frame(container)
        self._build_kanban(kanban)
        self.zones["kanban"] = kanban

        timeline = ttk.Frame(container)
        self._build_timeline(timeline)
        self.zones["timeline"] = timeline

        analytics = ttk.Frame(container)
        self._build_analytics(analytics)
        self.zones["analytics"] = analytics

    def _build_analytics(self, parent: ttk.Frame) -> None:
        toolbar = ttk.Frame(parent, padding=(8, 8))
        toolbar.pack(fill="x")
        self._mk_button(toolbar, "Обновить", self._load_dashboard_data).pack(side=LEFT, padx=2)

        self.analytics_filter_panel = ttk.Frame(parent, padding=(8, 8))
        self._build_analytics_filter_panel(self.analytics_filter_panel)

        content = ttk.Frame(parent, padding=(8, 8))
        content.pack(fill=BOTH, expand=True)
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)

        self.analytics_content_canvas = Canvas(content, highlightthickness=0, bd=0, bg=self._theme_color("surface_bg", "#F7F8F5"))
        analytics_vscroll = ttk.Scrollbar(content, orient=VERTICAL, command=self.analytics_content_canvas.yview)
        self.analytics_content_canvas.configure(yscrollcommand=analytics_vscroll.set)
        self.analytics_content_canvas.grid(row=0, column=0, sticky="nsew")
        analytics_vscroll.grid(row=0, column=1, sticky="ns")

        self.analytics_content_inner = ttk.Frame(self.analytics_content_canvas, style="Surface.TFrame")
        self.analytics_content_window = self.analytics_content_canvas.create_window((0, 0), window=self.analytics_content_inner, anchor="nw")
        self.analytics_content_inner.bind(
            "<Configure>",
            lambda _e: self.analytics_content_canvas.configure(scrollregion=self.analytics_content_canvas.bbox("all")),
        )
        self.analytics_content_canvas.bind(
            "<Configure>",
            lambda e: self.analytics_content_canvas.itemconfigure(self.analytics_content_window, width=max(1, int(getattr(e, "width", 1)))),
        )

        self.analytics_content_inner.grid_columnconfigure(0, weight=1, uniform="analytics")
        self.analytics_content_inner.grid_columnconfigure(1, weight=1, uniform="analytics")
        self.analytics_charts = {}
        chart_defs = [
            ("status_distribution", "\u0420\u0430\u0441\u043f\u0440\u0435\u0434\u0435\u043b\u0435\u043d\u0438\u0435 \u043f\u043e \u0441\u0442\u0430\u0442\u0443\u0441\u0430\u043c"),
            ("wip_by_executor", "WIP \u043f\u043e \u0438\u0441\u043f\u043e\u043b\u043d\u0438\u0442\u0435\u043b\u044f\u043c"),
            ("throughput_by_week", "\u041f\u0440\u043e\u043f\u0443\u0441\u043a\u043d\u0430\u044f \u0441\u043f\u043e\u0441\u043e\u0431\u043d\u043e\u0441\u0442\u044c \u043f\u043e \u043d\u0435\u0434\u0435\u043b\u044f\u043c"),
            ("cycle_time_by_project", "Cycle time \u043f\u043e \u043f\u0440\u043e\u0435\u043a\u0442\u0430\u043c"),
            ("lead_time_by_pocket", "Lead time \u043f\u043e \u043a\u0430\u0440\u043c\u0430\u043d\u0430\u043c"),
            ("overdue_tasks", "\u041f\u0440\u043e\u0441\u0440\u043e\u0447\u0435\u043d\u043d\u044b\u0435 \u0437\u0430\u0434\u0430\u0447\u0438"),
            ("pause_ratio_by_executor", "\u0414\u043e\u043b\u044f \u043f\u0430\u0443\u0437 \u043f\u043e \u0438\u0441\u043f\u043e\u043b\u043d\u0438\u0442\u0435\u043b\u044f\u043c"),
            ("queue_age", "\u0412\u043e\u0437\u0440\u0430\u0441\u0442 \u043e\u0447\u0435\u0440\u0435\u0434\u0438"),
        ]
        for idx, (key, title) in enumerate(chart_defs):
            card = ttk.Labelframe(self.analytics_content_inner, text=title, style="KanbanColumn.TLabelframe")
            card.grid(row=idx // 2, column=idx % 2, sticky="nsew", padx=6, pady=6)
            canvas = Canvas(card, height=190, highlightthickness=0, bd=0, bg=self._theme_color("surface_panel", "#FFFFFF"))
            canvas.pack(fill=BOTH, expand=True)
            self.analytics_charts[key] = canvas

        details_wrap = ttk.Labelframe(self.analytics_content_inner, text="Детализация", style="KanbanColumn.TLabelframe")
        details_wrap.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=6, pady=(8, 6))
        details_wrap.grid_columnconfigure(0, weight=1)
        details_wrap.grid_rowconfigure(0, weight=1)
        cols = ("id", "description", "status", "project_name", "pocket_name", "executor_full_name", "date_created", "date_done")
        self.analytics_details_tree = ttk.Treeview(details_wrap, columns=cols, show="headings")
        headers = {
            "id": "ID",
            "description": "Описание",
            "status": "Статус",
            "project_name": "Проект",
            "pocket_name": "Карман",
            "executor_full_name": "Исполнитель",
            "date_created": "Создана",
            "date_done": "Завершена",
        }
        for col in cols:
            self.analytics_details_tree.heading(col, text=headers[col])
            self.analytics_details_tree.column(col, width=120, anchor="w")
        self.analytics_details_tree.column("id", width=70, anchor="center")
        self.analytics_details_tree.column("description", width=320, anchor="w")
        self.analytics_details_tree.grid(row=0, column=0, sticky="nsew")
        details_scroll = ttk.Scrollbar(details_wrap, orient=VERTICAL, command=self.analytics_details_tree.yview)
        self.analytics_details_tree.configure(yscrollcommand=details_scroll.set)
        details_scroll.grid(row=0, column=1, sticky="ns")
        self.analytics_details_tree.bind("<Double-1>", self._on_analytics_details_double_click)

        self.analytics_bottom_controls = ttk.Frame(parent, padding=(8, 8))
        self.analytics_bottom_controls.pack(fill="x")
        self._mk_button(self.analytics_bottom_controls, "Фильтр", self._toggle_analytics_filter_panel).pack(side=LEFT, padx=2)
        self._mk_button(self.analytics_bottom_controls, "Сброс фильтра", self._reset_kanban_filters).pack(side=LEFT, padx=2)
        self.analytics_clear_drill_btn = self._mk_button(self.analytics_bottom_controls, "Снять детализацию", self._clear_analytics_drilldown)
        self.analytics_clear_drill_btn.pack(side=LEFT, padx=(2, 10))
        self.analytics_clear_drill_btn.state(["disabled"])
        self.analytics_filter_label = ttk.Label(self.analytics_bottom_controls, textvariable=self.analytics_filter_summary_var, style="Surface.TLabel", cursor="hand2")
        self.analytics_filter_label.pack(side=LEFT, padx=12)
        self.analytics_filter_label.bind("<Enter>", self._show_filter_tooltip)
        self.analytics_filter_label.bind("<Leave>", self._hide_filter_tooltip)
        self.analytics_session_label = ttk.Label(self.analytics_bottom_controls, textvariable=self.session_var, cursor="hand2", style="Session.TLabel", padding=(8, 2))
        self.analytics_session_label.pack(side=RIGHT, padx=6)
        self.analytics_session_label.bind("<Button-1>", self._on_session_click)

        self._apply_analytics_preset(DEFAULT_PRESET_NAME)
        self._refresh_analytics()

    def _build_analytics_filter_panel(self, parent: ttk.Frame) -> None:
        presets_bar = ttk.Frame(parent)
        presets_bar.pack(fill="x", pady=(0, 6))
        ttk.Label(presets_bar, text="Пресет:").pack(side=LEFT)
        self.analytics_preset_var = StringVar(value=DEFAULT_PRESET_NAME)
        self.analytics_preset_combo = ttk.Combobox(
            presets_bar,
            textvariable=self.analytics_preset_var,
            values=sorted(self.presets.keys()),
            state="readonly",
            width=28,
        )
        self.analytics_preset_combo.pack(side=LEFT, padx=6)
        self._mk_button(presets_bar, "Применить", self._apply_selected_analytics_preset).pack(side=LEFT, padx=2)
        self._mk_button(presets_bar, "Сохранить текущий", self._save_current_analytics_preset).pack(side=LEFT, padx=2)
        self._mk_button(presets_bar, "Переименовать", self._rename_analytics_preset).pack(side=LEFT, padx=2)
        self._mk_button(presets_bar, "Удалить", self._delete_analytics_preset).pack(side=LEFT, padx=2)

        self.analytics_rows_holder = ttk.Frame(parent)
        self.analytics_rows_holder.pack(fill="x")
        controls = ttk.Frame(parent)
        controls.pack(fill="x", pady=(6, 0))
        self._mk_button(controls, "+ Условие", self._add_analytics_filter_row).pack(side=LEFT)
        self._mk_button(controls, "Применить", self._apply_analytics_filters).pack(side=LEFT, padx=4)

    def _toggle_analytics_filter_panel(self) -> None:
        self.analytics_filter_visible = not self.analytics_filter_visible
        if self.analytics_filter_visible:
            self.analytics_filter_panel.pack(fill="x", before=self.analytics_bottom_controls)
        else:
            self.analytics_filter_panel.pack_forget()
        self._sync_global_filter_context_from_rows(
            self.analytics_filter_rows,
            zone="analytics",
            preset_name=self.analytics_preset_var.get() if "analytics_preset_var" in self.__dict__ else DEFAULT_PRESET_NAME,
            visible=self.analytics_filter_visible,
        )

    def _add_analytics_filter_row(self, field: str = "status", op: str = "==", value: str = "", logic: str = "AND") -> None:
        row = ttk.Frame(self.analytics_rows_holder)
        row.pack(fill="x", pady=2)
        logic_var = StringVar(value=logic)
        field_var = StringVar(value=field)
        op_var = StringVar(value=op)
        value_var = StringVar(value=value)
        if self.analytics_filter_rows:
            ttk.Combobox(row, textvariable=logic_var, values=["AND", "OR"], width=6, state="readonly").pack(side=LEFT, padx=2)
        else:
            ttk.Label(row, text="").pack(side=LEFT, padx=2)
        ttk.Combobox(
            row,
            textvariable=field_var,
            values=[
                "id", "description", "status", "date_created", "date_start_work", "date_done",
                "executor_full_name", "executor_user_id", "customer", "code_link", "project_id",
                "project_name", "pocket_id", "pocket_name",
            ],
            width=18,
            state="readonly",
        ).pack(side=LEFT, padx=2)
        ttk.Combobox(row, textvariable=op_var, values=["==", "!=", "in", "contains", "between", ">", "<", ">=", "<="], width=10, state="readonly").pack(side=LEFT, padx=2)
        ttk.Entry(row, textvariable=value_var, width=36).pack(side=LEFT, padx=2)
        self._mk_button(row, "x", lambda r=row: self._remove_analytics_filter_row(r), width=3).pack(side=LEFT, padx=2)
        self.analytics_filter_rows.append(FilterRow(row, logic_var, field_var, op_var, value_var))
        self._refresh_global_filter_indicators()

    def _remove_analytics_filter_row(self, row_frame: ttk.Frame) -> None:
        for idx, item in enumerate(self.analytics_filter_rows):
            if item.frame == row_frame:
                item.frame.destroy()
                self.analytics_filter_rows.pop(idx)
                break
        self._apply_analytics_filters()

    def _apply_analytics_filters(self) -> None:
        self._sync_global_filter_context_from_rows(
            self.analytics_filter_rows,
            zone="analytics",
            preset_name=self.analytics_preset_var.get() if hasattr(self, "analytics_preset_var") else DEFAULT_PRESET_NAME,
            visible=self.analytics_filter_visible,
        )
        self._apply_global_filter_context_to_zone("dashboard")
        self._apply_global_filter_context_to_zone("kanban")
        self._apply_global_filter_context_to_zone("timeline")
        self._apply_global_filter_context_to_zone("analytics")
        self._apply_global_filter_context_to_zone("analytics")
        if hasattr(self, "preset_var"):
            preset_name = self.global_filter_context.preset_name
            self.preset_var.set(preset_name if preset_name in self.presets else DEFAULT_PRESET_NAME)
        if hasattr(self, "kanban_preset_var"):
            preset_name = self.global_filter_context.preset_name
            self.kanban_preset_var.set(preset_name if preset_name in self.kanban_presets else DEFAULT_PRESET_NAME)
        if "timeline_preset_var" in self.__dict__:
            preset_name = self.global_filter_context.preset_name
            self.timeline_preset_var.set(preset_name if preset_name in self.presets else DEFAULT_PRESET_NAME)
        self._refresh_dashboard_top_table_from_filter_context()
        self._refresh_dashboard_bottom_table_from_selection_and_filter()
        self._refresh_kanban_board()
        self._refresh_timeline()
        self._refresh_analytics()

    def _apply_selected_analytics_preset(self) -> None:
        self._apply_analytics_preset(self.analytics_preset_var.get())
        self._apply_analytics_filters()

    def _apply_analytics_preset(self, name: str) -> None:
        preset = self.presets.get(name)
        if not preset:
            return
        for row in self.analytics_filter_rows:
            row.frame.destroy()
        self.analytics_filter_rows.clear()
        for cond in preset.get("filters", []):
            self._add_analytics_filter_row(
                field=cond.get("field", "status"),
                op=cond.get("op", "=="),
                value=cond.get("value", ""),
                logic=cond.get("logic", "AND"),
            )
        self.analytics_filter_visible = bool(preset.get("filter_visible", False))
        if self.analytics_filter_visible:
            self.analytics_filter_panel.pack(fill="x", before=self.analytics_bottom_controls)
        else:
            self.analytics_filter_panel.pack_forget()
        self._sync_global_filter_context_from_rows(self.analytics_filter_rows, zone="analytics", preset_name=name, visible=self.analytics_filter_visible)

    def _save_current_analytics_preset(self) -> None:
        name = simpledialog.askstring("Сохранить пресет", "Имя пресета:", parent=self)
        if not name:
            return
        self.presets[name] = {
            "filter_visible": self.analytics_filter_visible,
            "filters": self._serialize_filter_rows(self.analytics_filter_rows),
        }
        self._save_presets(self.presets)
        self._refresh_preset_combo()
        if hasattr(self, "analytics_preset_combo"):
            self.analytics_preset_combo["values"] = sorted(self.presets.keys())
        self.analytics_preset_var.set(name)

    def _rename_analytics_preset(self) -> None:
        old = self.analytics_preset_var.get()
        if old not in self.presets:
            return
        new = simpledialog.askstring("Переименовать пресет", "Новое имя:", initialvalue=old, parent=self)
        if not new or new == old:
            return
        self.presets[new] = self.presets.pop(old)
        self._save_presets(self.presets)
        self._refresh_preset_combo()
        if hasattr(self, "analytics_preset_combo"):
            self.analytics_preset_combo["values"] = sorted(self.presets.keys())
        self.analytics_preset_var.set(new)

    def _delete_analytics_preset(self) -> None:
        name = self.analytics_preset_var.get()
        if name == DEFAULT_PRESET_NAME:
            messagebox.showwarning("Ограничение", "Пресет по умолчанию удалить нельзя.")
            return
        if name in self.presets:
            del self.presets[name]
            self._save_presets(self.presets)
            self._refresh_preset_combo()
            if hasattr(self, "analytics_preset_combo"):
                self.analytics_preset_combo["values"] = sorted(self.presets.keys())
            self.analytics_preset_var.set(DEFAULT_PRESET_NAME)
            self._apply_analytics_preset(DEFAULT_PRESET_NAME)

    def _build_dashboard(self, parent: ttk.Frame) -> None:
        toolbar = ttk.Frame(parent, padding=(8, 8))
        toolbar.pack(fill="x")
        self._mk_button(toolbar, "Обновить", self._load_dashboard_data).pack(side=LEFT)

        content = ttk.Frame(parent, padding=(8, 8))
        content.pack(fill=BOTH, expand=True)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=1)

        top = ttk.Frame(content)
        top.grid(row=0, column=0, sticky="nsew")
        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(0, weight=1)
        bottom = ttk.Frame(content)
        bottom.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        bottom.grid_columnconfigure(0, weight=1)
        bottom.grid_rowconfigure(0, weight=1)

        top_cols = (
            "pocket_id",
            "pocket_name",
            "project_id",
            "project_name",
            "project_code",
            "date_start",
            "date_end",
            "status",
            "owner",
            "owner_it",
        )
        self.top_tree = ttk.Treeview(top, columns=top_cols, show="headings")
        for col in top_cols:
            self.top_tree.heading(col, text=TOP_COLUMN_TITLES.get(col, col))
            self.top_tree.column(col, width=120, anchor="w")
        self.top_tree.column("pocket_id", anchor="center")
        self.top_tree.column("project_id", anchor="center")
        top_vscroll = ttk.Scrollbar(top, orient=VERTICAL, command=self.top_tree.yview)
        self.top_tree.configure(yscrollcommand=top_vscroll.set)
        self.top_tree.grid(row=0, column=0, sticky="nsew")
        top_vscroll.grid(row=0, column=1, sticky="ns")
        self.top_tree.configure(height=4)
        self.top_tree.bind("<<TreeviewSelect>>", self._on_top_select)
        self.top_tree.bind("<Double-1>", self._on_top_double_click)

        bottom_cols = (
            "id",
            "description",
            "status",
            "date_created",
            "date_start_work",
            "date_done",
            "executor_full_name",
            "customer",
            "code_link",
        )
        self.bottom_tree = ttk.Treeview(bottom, columns=bottom_cols, show="headings")
        for col in bottom_cols:
            self.bottom_tree.heading(col, text=BOTTOM_COLUMN_TITLES.get(col, col))
            self.bottom_tree.column(col, width=150, anchor="w")
        self.bottom_tree.column("id", anchor="center")
        self.bottom_tree.column("description", width=360)
        bottom_vscroll = ttk.Scrollbar(bottom, orient=VERTICAL, command=self.bottom_tree.yview)
        self.bottom_tree.configure(yscrollcommand=bottom_vscroll.set)
        self.bottom_tree.grid(row=0, column=0, sticky="nsew")
        bottom_vscroll.grid(row=0, column=1, sticky="ns")
        self.bottom_tree.bind("<Double-1>", self._on_bottom_double_click)

        self.filter_panel = ttk.Frame(parent, padding=(8, 8))
        self._build_filter_panel(self.filter_panel)

        self.bottom_controls = ttk.Frame(parent, padding=(8, 8))
        self.bottom_controls.pack(fill="x")
        self._mk_button(self.bottom_controls, "Фильтр", self._toggle_filter_panel).pack(side=LEFT, padx=2)
        self._mk_button(self.bottom_controls, "Сброс фильтра", self._reset_filters).pack(side=LEFT, padx=6)
        self.filter_summary_label = ttk.Label(
            self.bottom_controls,
            textvariable=self.filter_summary_var,
            style="Surface.TLabel",
            cursor="hand2",
        )
        self.filter_summary_label.pack(side=LEFT, padx=12)
        self.filter_summary_label.bind("<Enter>", self._show_filter_tooltip)
        self.filter_summary_label.bind("<Leave>", self._hide_filter_tooltip)
        ttk.Checkbutton(
            self.bottom_controls,
            text="Показывать проекты без задач",
            variable=self.show_projects_without_tasks_var,
            command=self._apply_filters,
        ).pack(side=RIGHT, padx=4)
        self.dashboard_session_label = ttk.Label(
            self.bottom_controls,
            textvariable=self.session_var,
            cursor="hand2",
            style="Session.TLabel",
            padding=(8, 2),
        )
        self.dashboard_session_label.pack(side=RIGHT, padx=6)
        self.dashboard_session_label.bind("<Button-1>", self._on_session_click)

    def _build_filter_panel(self, parent: ttk.Frame) -> None:
        presets_bar = ttk.Frame(parent)
        presets_bar.pack(fill="x", pady=(0, 6))

        ttk.Label(presets_bar, text="Пресет:").pack(side=LEFT)
        self.preset_var = StringVar(value=DEFAULT_PRESET_NAME)
        self.preset_combo = ttk.Combobox(
            presets_bar,
            textvariable=self.preset_var,
            values=sorted(self.presets.keys()),
            state="readonly",
            width=28,
        )
        self.preset_combo.pack(side=LEFT, padx=6)
        self._mk_button(presets_bar, "Применить", self._apply_selected_preset).pack(side=LEFT, padx=2)
        self._mk_button(presets_bar, "Сохранить текущий", self._save_current_preset).pack(side=LEFT, padx=2)
        self._mk_button(presets_bar, "Переименовать", self._rename_preset).pack(side=LEFT, padx=2)
        self._mk_button(presets_bar, "Удалить", self._delete_preset).pack(side=LEFT, padx=2)

        self.rows_holder = ttk.Frame(parent)
        self.rows_holder.pack(fill="x")

        controls = ttk.Frame(parent)
        controls.pack(fill="x", pady=(6, 0))
        self._mk_button(controls, "+ Условие", self._add_filter_row).pack(side=LEFT)
        self._mk_button(controls, "Применить", self._apply_filters).pack(side=LEFT)

        self._apply_preset(DEFAULT_PRESET_NAME)
        self._refresh_filter_indicator()

    def _build_kanban(self, parent: ttk.Frame) -> None:
        toolbar = ttk.Frame(parent, padding=(8, 8))
        toolbar.pack(fill="x")
        self._mk_button(toolbar, "Обновить", self._load_dashboard_data).pack(side=LEFT)

        self.kanban_filter_panel = ttk.Frame(parent, padding=(8, 8))
        self._build_kanban_filter_panel(self.kanban_filter_panel)

        board = ttk.Frame(parent, padding=(8, 8))
        self.kanban_board_container = board
        board.pack(fill=BOTH, expand=True)
        self.kanban_columns: dict[str, ttk.Frame] = {}
        self.kanban_column_frames: dict[str, ttk.LabelFrame] = {}
        self.kanban_column_canvases: dict[str, Canvas] = {}
        self.kanban_column_windows: dict[str, int] = {}
        columns = [
            ("queue", "Очередь"),
            ("created", "Создана"),
            ("in_progress", "В работе"),
            ("paused", "Приостановлена"),
            ("done", "Завершена"),
        ]
        for idx, (key, title) in enumerate(columns):
            col = ttk.LabelFrame(board, text=title, padding=(8, 8), style="KanbanColumn.TLabelframe")
            col.grid(row=0, column=idx, sticky="nsew", padx=4)
            board.columnconfigure(idx, weight=1, uniform="kanban")
            col.grid_columnconfigure(0, weight=1)
            col.grid_rowconfigure(0, weight=1)
            canvas = Canvas(
                col,
                highlightthickness=0,
                bd=0,
                bg=self._theme_color("surface_bg", "#F7F8F5"),
            )
            vscroll = ttk.Scrollbar(col, orient=VERTICAL, command=canvas.yview)
            canvas.configure(yscrollcommand=vscroll.set)
            canvas.grid(row=0, column=0, sticky="nsew")
            vscroll.grid(row=0, column=1, sticky="ns")
            inner = ttk.Frame(canvas, style="Surface.TFrame")
            window_id = canvas.create_window((0, 0), window=inner, anchor="nw")
            inner.bind("<Configure>", lambda _e, c=canvas: c.configure(scrollregion=c.bbox("all")))
            canvas.bind(
                "<Configure>",
                lambda e, c=canvas, w=window_id: c.itemconfigure(w, width=max(1, int(getattr(e, "width", 1)))),
            )
            self.kanban_column_frames[key] = col
            self.kanban_columns[key] = inner
            self.kanban_column_canvases[key] = canvas
            self.kanban_column_windows[key] = window_id
        board.rowconfigure(0, weight=1)

        self.kanban_bottom_controls = ttk.Frame(parent, padding=(8, 8))
        self.kanban_bottom_controls.pack(fill="x")
        self._mk_button(self.kanban_bottom_controls, "Фильтр", self._toggle_kanban_filter_panel).pack(side=LEFT, padx=2)
        self._mk_button(self.kanban_bottom_controls, "Сброс фильтра", self._reset_kanban_filters).pack(side=LEFT, padx=6)
        self.kanban_filter_label = ttk.Label(
            self.kanban_bottom_controls,
            textvariable=self.kanban_filter_summary_var,
            style="Surface.TLabel",
            cursor="hand2",
        )
        self.kanban_filter_label.pack(side=LEFT, padx=10)
        self.kanban_filter_label.bind("<Enter>", self._show_kanban_filter_tooltip)
        self.kanban_filter_label.bind("<Leave>", self._hide_kanban_filter_tooltip)

        self.session_label = ttk.Label(
            self.kanban_bottom_controls,
            textvariable=self.session_var,
            cursor="hand2",
            style="Session.TLabel",
            padding=(8, 2),
        )
        self.session_label.pack(side=RIGHT, padx=6)
        self.session_label.bind("<Button-1>", self._on_session_click)

        self._apply_kanban_preset(DEFAULT_PRESET_NAME)
        self._refresh_kanban_filter_indicator()

    def _build_kanban_filter_panel(self, parent: ttk.Frame) -> None:
        presets_bar = ttk.Frame(parent)
        presets_bar.pack(fill="x", pady=(0, 6))
        ttk.Label(presets_bar, text="Пресет:").pack(side=LEFT)
        self.kanban_preset_var = StringVar(value=DEFAULT_PRESET_NAME)
        self.kanban_preset_combo = ttk.Combobox(
            presets_bar,
            textvariable=self.kanban_preset_var,
            values=sorted(self.kanban_presets.keys()),
            state="readonly",
            width=28,
        )
        self.kanban_preset_combo.pack(side=LEFT, padx=6)
        self._mk_button(presets_bar, "Применить", self._apply_selected_kanban_preset).pack(side=LEFT, padx=2)
        self._mk_button(presets_bar, "Сохранить текущий", self._save_current_kanban_preset).pack(side=LEFT, padx=2)
        self._mk_button(presets_bar, "Переименовать", self._rename_kanban_preset).pack(side=LEFT, padx=2)
        self._mk_button(presets_bar, "Удалить", self._delete_kanban_preset).pack(side=LEFT, padx=2)

        self.kanban_rows_holder = ttk.Frame(parent)
        self.kanban_rows_holder.pack(fill="x")
        controls = ttk.Frame(parent)
        controls.pack(fill="x", pady=(6, 0))
        self._mk_button(controls, "+ Условие", self._add_kanban_filter_row).pack(side=LEFT)
        self._mk_button(controls, "Применить", self._apply_kanban_filters).pack(side=LEFT, padx=4)

    def _timeline_default_month_bounds(self) -> tuple[date, date]:
        today = date.today()
        first = date(today.year, today.month, 1)
        last = date(today.year, today.month, monthrange(today.year, today.month)[1])
        return first, last


    def _truncate_timeline_text(self, text: Any, max_len: int = 40) -> str:
        value = str(text or "")
        if len(value) <= max_len:
            return value
        return value[: max_len - 3] + "..."

    def _on_timeline_tree_motion_show_tooltip(self, event: object) -> None:
        if not self.timeline_rows_tree:
            return
        x = int(getattr(event, "x", 0))
        y = int(getattr(event, "y", 0))
        row_id = self.timeline_rows_tree.identify_row(y)
        column = self.timeline_rows_tree.identify_column(x)
        if not row_id or column != "#2":
            self._timeline_hover_task_id = None
            self._hide_widget_tooltip()
            return
        try:
            task_id = int(row_id)
        except Exception:
            self._timeline_hover_task_id = None
            self._hide_widget_tooltip()
            return
        full_text = self.timeline_full_text_by_task_id.get(task_id, "")
        short_text = self._truncate_timeline_text(full_text)
        if not full_text or full_text == short_text:
            self._timeline_hover_task_id = None
            self._hide_widget_tooltip()
            return
        if self._timeline_hover_task_id == task_id:
            return
        self._timeline_hover_task_id = task_id
        self._show_widget_tooltip(event, full_text)

    def _load_timeline_split_ratio(self) -> float:
        path = _ui_config_file()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                ratio = float(data.get("timeline_split_ratio", TIMELINE_DEFAULT_SPLIT_RATIO))
                return min(0.8, max(0.2, ratio))
            except Exception:
                pass
        return TIMELINE_DEFAULT_SPLIT_RATIO

    def _save_timeline_split_ratio(self, ratio: float) -> None:
        path = _ui_config_file()
        data: dict[str, Any] = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    data = loaded
            except Exception:
                data = {}
        data["timeline_split_ratio"] = min(0.8, max(0.2, ratio))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _restore_timeline_pane_ratio(self) -> None:
        if "timeline_paned" not in self.__dict__:
            return
        if not self.timeline_paned or not self.timeline_paned.winfo_exists():
            return
        width = int(self.timeline_paned.winfo_width())
        if width <= 8:
            return
        desired = int(width * self.timeline_split_ratio)
        desired = min(max(120, desired), width - 120)
        try:
            self.timeline_paned.sashpos(0, desired)
        except Exception:
            return

    def _on_timeline_pane_released(self, _event: object) -> None:
        if "timeline_paned" not in self.__dict__:
            return
        if not self.timeline_paned or not self.timeline_paned.winfo_exists():
            return
        width = int(self.timeline_paned.winfo_width())
        if width <= 8:
            return
        try:
            sash = int(self.timeline_paned.sashpos(0))
        except Exception:
            return
        ratio = sash / float(width)
        self.timeline_split_ratio = min(0.8, max(0.2, ratio))
        self._save_timeline_split_ratio(self.timeline_split_ratio)

    def _on_timeline_paned_configure(self, _event: object) -> None:
        self.after_idle(self._restore_timeline_pane_ratio)

    def _build_timeline(self, parent: ttk.Frame) -> None:
        toolbar = ttk.Frame(parent, padding=(8, 8))
        toolbar.pack(fill="x")
        self._mk_button(toolbar, "Обновить", self._load_dashboard_data).pack(side=LEFT)

        period_bar = ttk.Frame(parent, padding=(8, 0, 8, 8))
        period_bar.pack(fill="x")
        ttk.Label(period_bar, text="Начало:").pack(side=LEFT)
        ttk.Entry(period_bar, textvariable=self.timeline_slice_start_var, width=12).pack(side=LEFT, padx=(4, 8))
        ttk.Label(period_bar, text="Окончание:").pack(side=LEFT)
        ttk.Entry(period_bar, textvariable=self.timeline_slice_end_var, width=12).pack(side=LEFT, padx=(4, 8))
        self._mk_button(period_bar, "Применить период", self._apply_timeline_period).pack(side=LEFT, padx=2)
        self._mk_button(period_bar, "Сброс периода", self._reset_timeline_period).pack(side=LEFT, padx=6)

        self.timeline_filter_panel = ttk.Frame(parent, padding=(8, 8))
        self._build_timeline_filter_panel(self.timeline_filter_panel)

        content = ttk.Frame(parent, padding=(8, 8))
        content.pack(fill=BOTH, expand=True)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)

        self.timeline_paned = ttk.Panedwindow(content, orient="horizontal")
        self.timeline_paned.grid(row=0, column=0, sticky="nsew")

        left = ttk.Frame(self.timeline_paned)
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(0, weight=1)

        right = ttk.Frame(self.timeline_paned)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)

        self.timeline_paned.add(left, weight=3)
        self.timeline_paned.add(right, weight=5)
        self.timeline_paned.bind("<ButtonRelease-1>", self._on_timeline_pane_released)
        self.timeline_paned.bind("<Configure>", self._on_timeline_paned_configure)

        cols = ("id", "description", "status", "executor_full_name", "date_start_work", "date_done")
        self.timeline_rows_tree = ttk.Treeview(left, columns=cols, show="headings", style="Timeline.Treeview")
        self.timeline_rows_tree.heading("id", text="ID")
        self.timeline_rows_tree.heading("description", text="Задача")
        self.timeline_rows_tree.heading("status", text="Статус")
        self.timeline_rows_tree.heading("executor_full_name", text="Исполнитель")
        self.timeline_rows_tree.heading("date_start_work", text="Старт")
        self.timeline_rows_tree.heading("date_done", text="Завершена")
        self.timeline_rows_tree.column("id", width=70, anchor="center")
        self.timeline_rows_tree.column("description", width=360, anchor="w")
        self.timeline_rows_tree.column("status", width=140, anchor="w")
        self.timeline_rows_tree.column("executor_full_name", width=180, anchor="w")
        self.timeline_rows_tree.column("date_start_work", width=110, anchor="center")
        self.timeline_rows_tree.column("date_done", width=110, anchor="center")
        self.timeline_rows_tree.grid(row=0, column=0, sticky="nsew")
        self.timeline_rows_tree.bind("<Double-1>", self._on_timeline_double_click)
        self.timeline_rows_tree.bind("<Motion>", self._on_timeline_tree_motion_show_tooltip)
        self.timeline_rows_tree.bind("<Leave>", self._hide_widget_tooltip)
        self.timeline_rows_tree.bind("<ButtonPress>", self._hide_widget_tooltip)

        self.timeline_canvas = Canvas(right, highlightthickness=0, bd=0, bg=self._theme_color("surface_panel", "#FFFFFF"))
        self.timeline_vscroll = ttk.Scrollbar(right, orient=VERTICAL, command=self._timeline_canvas_yview)
        self.timeline_hscroll = ttk.Scrollbar(right, orient="horizontal", command=self.timeline_canvas.xview)
        self.timeline_tree_scroll = ttk.Scrollbar(left, orient=VERTICAL, command=self._timeline_tree_yview)
        self.timeline_rows_tree.configure(yscrollcommand=self._timeline_tree_yscroll)
        self.timeline_canvas.configure(yscrollcommand=self._timeline_canvas_yscroll, xscrollcommand=self.timeline_hscroll.set)
        self.timeline_canvas.grid(row=0, column=0, sticky="nsew")
        self.timeline_tree_scroll.grid(row=0, column=1, sticky="ns")
        self.timeline_vscroll.grid(row=0, column=1, sticky="ns")
        self.timeline_hscroll.grid(row=1, column=0, sticky="ew")

        self.timeline_bottom_controls = ttk.Frame(parent, padding=(8, 8))
        self.timeline_bottom_controls.pack(fill="x")
        self._mk_button(self.timeline_bottom_controls, "Фильтр", self._toggle_timeline_filter_panel).pack(side=LEFT, padx=2)
        self.timeline_filter_label = ttk.Label(self.timeline_bottom_controls, textvariable=self.timeline_filter_summary_var, style="Surface.TLabel", cursor="hand2")
        self.timeline_filter_label.pack(side=LEFT, padx=12)
        self.timeline_filter_label.bind("<Enter>", self._show_filter_tooltip)
        self.timeline_filter_label.bind("<Leave>", self._hide_filter_tooltip)
        self.timeline_session_label = ttk.Label(self.timeline_bottom_controls, textvariable=self.session_var, cursor="hand2", style="Session.TLabel", padding=(8, 2))
        self.timeline_session_label.pack(side=RIGHT, padx=6)
        self.timeline_session_label.bind("<Button-1>", self._on_session_click)

        self._reset_timeline_period(silent=True)
        self._apply_timeline_preset(DEFAULT_PRESET_NAME)
        self._refresh_timeline_filter_indicator()
        self.after_idle(self._restore_timeline_pane_ratio)

    def _build_timeline_filter_panel(self, parent: ttk.Frame) -> None:
        presets_bar = ttk.Frame(parent)
        presets_bar.pack(fill="x", pady=(0, 6))
        ttk.Label(presets_bar, text="Пресет:").pack(side=LEFT)
        self.timeline_preset_var = StringVar(value=DEFAULT_PRESET_NAME)
        self.timeline_preset_combo = ttk.Combobox(
            presets_bar,
            textvariable=self.timeline_preset_var,
            values=sorted(self.presets.keys()),
            state="readonly",
            width=28,
        )
        self.timeline_preset_combo.pack(side=LEFT, padx=6)
        self._mk_button(presets_bar, "Применить", self._apply_selected_timeline_preset).pack(side=LEFT, padx=2)
        self._mk_button(presets_bar, "Сохранить текущий", self._save_current_timeline_preset).pack(side=LEFT, padx=2)
        self._mk_button(presets_bar, "Переименовать", self._rename_timeline_preset).pack(side=LEFT, padx=2)
        self._mk_button(presets_bar, "Удалить", self._delete_timeline_preset).pack(side=LEFT, padx=2)

        self.timeline_rows_holder = ttk.Frame(parent)
        self.timeline_rows_holder.pack(fill="x")
        controls = ttk.Frame(parent)
        controls.pack(fill="x", pady=(6, 0))
        self._mk_button(controls, "+ Условие", self._add_timeline_filter_row).pack(side=LEFT)
        self._mk_button(controls, "Применить", self._apply_timeline_filters).pack(side=LEFT, padx=4)

    def _toggle_timeline_filter_panel(self) -> None:
        self.timeline_filter_visible = not self.timeline_filter_visible
        if self.timeline_filter_visible:
            self.timeline_filter_panel.pack(fill="x", before=self.timeline_bottom_controls)
        else:
            self.timeline_filter_panel.pack_forget()
        self._sync_global_filter_context_from_rows(
            self.timeline_filter_rows,
            zone="timeline",
            preset_name=self.timeline_preset_var.get() if "timeline_preset_var" in self.__dict__ else DEFAULT_PRESET_NAME,
            visible=self.timeline_filter_visible,
        )

    def _add_timeline_filter_row(self, field: str = "status", op: str = "==", value: str = "", logic: str = "AND") -> None:
        row = ttk.Frame(self.timeline_rows_holder)
        row.pack(fill="x", pady=2)
        logic_var = StringVar(value=logic)
        field_var = StringVar(value=field)
        op_var = StringVar(value=op)
        value_var = StringVar(value=value)

        if self.timeline_filter_rows:
            ttk.Combobox(row, textvariable=logic_var, values=["AND", "OR"], width=6, state="readonly").pack(side=LEFT, padx=2)
        else:
            ttk.Label(row, text="").pack(side=LEFT, padx=2)

        ttk.Combobox(
            row,
            textvariable=field_var,
            values=[
                "id", "description", "status", "date_created", "date_start_work", "date_done",
                "executor_full_name", "executor_user_id", "customer", "code_link", "project_id",
                "project_name", "pocket_id", "pocket_name",
            ],
            width=18,
            state="readonly",
        ).pack(side=LEFT, padx=2)
        ttk.Combobox(row, textvariable=op_var, values=["==", "!=", "in", "contains", "between", ">", "<", ">=", "<="], width=10, state="readonly").pack(side=LEFT, padx=2)
        ttk.Entry(row, textvariable=value_var, width=36).pack(side=LEFT, padx=2)
        self._mk_button(row, "x", lambda r=row: self._remove_timeline_filter_row(r), width=3).pack(side=LEFT, padx=2)

        self.timeline_filter_rows.append(FilterRow(row, logic_var, field_var, op_var, value_var))
        self._refresh_timeline_filter_indicator()

    def _remove_timeline_filter_row(self, row_frame: ttk.Frame) -> None:
        for idx, item in enumerate(self.timeline_filter_rows):
            if item.frame == row_frame:
                item.frame.destroy()
                self.timeline_filter_rows.pop(idx)
                break
        self._apply_timeline_filters()

    def _apply_timeline_filters(self) -> None:
        self._sync_global_filter_context_from_rows(
            self.timeline_filter_rows,
            zone="timeline",
            preset_name=self.timeline_preset_var.get() if "timeline_preset_var" in self.__dict__ else DEFAULT_PRESET_NAME,
            visible=self.timeline_filter_visible,
        )
        self._apply_global_filter_context_to_zone("dashboard")
        self._apply_global_filter_context_to_zone("kanban")
        self._apply_global_filter_context_to_zone("timeline")
        if hasattr(self, "preset_var"):
            self.preset_var.set(self.global_filter_context.preset_name if self.global_filter_context.preset_name in self.presets else DEFAULT_PRESET_NAME)
        if hasattr(self, "kanban_preset_var"):
            self.kanban_preset_var.set(self.global_filter_context.preset_name if self.global_filter_context.preset_name in self.kanban_presets else DEFAULT_PRESET_NAME)
        if hasattr(self, "analytics_preset_var"):
            self.analytics_preset_var.set(self.global_filter_context.preset_name if self.global_filter_context.preset_name in self.presets else DEFAULT_PRESET_NAME)
        self._refresh_dashboard_top_table_from_filter_context()
        self._refresh_dashboard_bottom_table_from_selection_and_filter()
        self._refresh_kanban_board()
        self._refresh_timeline()
        self._refresh_analytics()

    def _apply_selected_timeline_preset(self) -> None:
        self._apply_timeline_preset(self.timeline_preset_var.get())
        self._apply_timeline_filters()

    def _apply_timeline_preset(self, name: str) -> None:
        preset = self.presets.get(name)
        if not preset:
            return
        for row in self.timeline_filter_rows:
            row.frame.destroy()
        self.timeline_filter_rows.clear()
        for cond in preset.get("filters", []):
            self._add_timeline_filter_row(
                field=cond.get("field", "status"),
                op=cond.get("op", "=="),
                value=cond.get("value", ""),
                logic=cond.get("logic", "AND"),
            )
        self.timeline_filter_visible = bool(preset.get("filter_visible", False))
        if self.timeline_filter_visible:
            self.timeline_filter_panel.pack(fill="x", before=self.timeline_bottom_controls)
        else:
            self.timeline_filter_panel.pack_forget()
        self._sync_global_filter_context_from_rows(self.timeline_filter_rows, zone="timeline", preset_name=name, visible=self.timeline_filter_visible)

    def _save_current_timeline_preset(self) -> None:
        name = simpledialog.askstring("Сохранить пресет", "Имя пресета:", parent=self)
        if not name:
            return
        self.presets[name] = {
            "filter_visible": self.timeline_filter_visible,
            "filters": self._serialize_filter_rows(self.timeline_filter_rows),
        }
        self._save_presets(self.presets)
        self._refresh_preset_combo()
        if hasattr(self, "timeline_preset_combo"):
            self.timeline_preset_combo["values"] = sorted(self.presets.keys())
        self.timeline_preset_var.set(name)

    def _rename_timeline_preset(self) -> None:
        old = self.timeline_preset_var.get()
        if old not in self.presets:
            return
        new = simpledialog.askstring("Переименовать пресет", "Новое имя:", initialvalue=old, parent=self)
        if not new or new == old:
            return
        self.presets[new] = self.presets.pop(old)
        self._save_presets(self.presets)
        self._refresh_preset_combo()
        if hasattr(self, "timeline_preset_combo"):
            self.timeline_preset_combo["values"] = sorted(self.presets.keys())
        self.timeline_preset_var.set(new)

    def _delete_timeline_preset(self) -> None:
        name = self.timeline_preset_var.get()
        if name == DEFAULT_PRESET_NAME:
            messagebox.showwarning("Ограничение", "Пресет по умолчанию удалить нельзя.")
            return
        if name in self.presets:
            del self.presets[name]
            self._save_presets(self.presets)
            self._refresh_preset_combo()
            if hasattr(self, "timeline_preset_combo"):
                self.timeline_preset_combo["values"] = sorted(self.presets.keys())
            self.timeline_preset_var.set(DEFAULT_PRESET_NAME)
            self._apply_timeline_preset(DEFAULT_PRESET_NAME)

    def _refresh_timeline_filter_indicator(self) -> None:
        self._refresh_global_filter_indicators()

    def _timeline_tree_yview(self, *args: Any) -> None:
        if not self.timeline_rows_tree or not self.timeline_canvas:
            return
        self.timeline_rows_tree.yview(*args)
        if not self._syncing_timeline_scroll:
            self._syncing_timeline_scroll = True
            try:
                first, _ = self.timeline_rows_tree.yview()
                self.timeline_canvas.yview_moveto(first)
            finally:
                self._syncing_timeline_scroll = False

    def _timeline_canvas_yview(self, *args: Any) -> None:
        if not self.timeline_rows_tree or not self.timeline_canvas:
            return
        self.timeline_canvas.yview(*args)
        if not self._syncing_timeline_scroll:
            self._syncing_timeline_scroll = True
            try:
                first, _ = self.timeline_canvas.yview()
                self.timeline_rows_tree.yview_moveto(first)
            finally:
                self._syncing_timeline_scroll = False

    def _timeline_tree_yscroll(self, first: str, last: str) -> None:
        if hasattr(self, "timeline_tree_scroll"):
            self.timeline_tree_scroll.set(first, last)
        if not self._syncing_timeline_scroll and self.timeline_canvas:
            self._syncing_timeline_scroll = True
            try:
                self.timeline_canvas.yview_moveto(float(first))
            finally:
                self._syncing_timeline_scroll = False

    def _timeline_canvas_yscroll(self, first: str, last: str) -> None:
        if hasattr(self, "timeline_vscroll"):
            self.timeline_vscroll.set(first, last)
        if not self._syncing_timeline_scroll and self.timeline_rows_tree:
            self._syncing_timeline_scroll = True
            try:
                self.timeline_rows_tree.yview_moveto(float(first))
            finally:
                self._syncing_timeline_scroll = False

    def _parse_iso_date(self, value: Any) -> date | None:
        if value in (None, ""):
            return None
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value))
        except Exception:
            return None

    def _task_timeline_bounds(self, task: dict[str, Any]) -> tuple[date, date]:
        start = self._parse_iso_date(task.get("date_start_work")) or self._parse_iso_date(task.get("date_created")) or date.today()
        end = self._parse_iso_date(task.get("date_done")) or date.today()
        if end < start:
            end = start
        return start, end

    def _timeline_intersects_slice(self, start: date, end: date, slice_start: date | None, slice_end: date | None) -> bool:
        left = slice_start or date.min
        right = slice_end or date.max
        return not (end < left or start > right)

    def _timeline_slice_bounds(self, *, show_errors: bool = False) -> tuple[date | None, date | None] | None:
        raw_start = self.timeline_slice_start_var.get().strip()
        raw_end = self.timeline_slice_end_var.get().strip()
        slice_start = self._parse_iso_date(raw_start)
        slice_end = self._parse_iso_date(raw_end)
        if raw_start and slice_start is None:
            if show_errors:
                messagebox.showerror("Timeline", "Неверная дата начала. Формат: YYYY-MM-DD")
            return None
        if raw_end and slice_end is None:
            if show_errors:
                messagebox.showerror("Timeline", "Неверная дата окончания. Формат: YYYY-MM-DD")
            return None
        if slice_start and slice_end and slice_start > slice_end:
            if show_errors:
                messagebox.showerror("Timeline", "Дата начала не может быть позже даты окончания.")
            return None
        return slice_start, slice_end

    def _apply_timeline_slice(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        bounds = self._timeline_slice_bounds(show_errors=False)
        if bounds is None:
            return rows
        slice_start, slice_end = bounds
        result: list[dict[str, Any]] = []
        for row in rows:
            start, end = self._task_timeline_bounds(row)
            if self._timeline_intersects_slice(start, end, slice_start, slice_end):
                result.append(row)
        return result

    def _apply_timeline_period(self) -> None:
        if self._timeline_slice_bounds(show_errors=True) is None:
            return
        self._refresh_timeline()

    def _reset_timeline_period(self, *, silent: bool = False) -> None:
        start, end = self._timeline_default_month_bounds()
        self.timeline_slice_start_var.set(start.isoformat())
        self.timeline_slice_end_var.set(end.isoformat())
        if not silent:
            self._refresh_timeline()

    def _draw_timeline_axis(self, min_date: date, max_date: date, left_pad: int, top_pad: int, row_h: int, row_count: int) -> int:
        if not self.timeline_canvas:
            return 16
        ppd = 16
        total_days = max(1, (max_date - min_date).days + 1)
        height = top_pad + row_count * row_h + 20
        today = date.today()
        for d in range(total_days + 1):
            dt = date.fromordinal(min_date.toordinal() + d)
            x = left_pad + d * ppd
            if dt == today:
                color = self._theme_color("info", "#3D6475")
                width = 2
            elif dt.weekday() == 0:
                color = self._theme_color("border", "#D8DDD8")
                width = 2
            else:
                color = self._theme_color("border", "#D8DDD8")
                width = 1
            self.timeline_canvas.create_line(x, top_pad - 14, x, height, fill=color, width=width)
            if d < total_days and (dt.weekday() == 0 or d == 0):
                self.timeline_canvas.create_text(
                    x + 2,
                    8,
                    anchor="nw",
                    text=dt.strftime("%d.%m"),
                    fill=self._theme_color("text_muted", "#5F6B6D"),
                )
        return ppd

    def _open_timeline_task_by_id(self, task_id: int) -> None:
        task = next((t for t in self.tasks_all if int(t.get("id", 0)) == int(task_id)), None)
        if task:
            self._open_task_form(mode="edit", task=task)

    def _on_timeline_double_click(self, event: object) -> None:
        if not self.timeline_rows_tree:
            return
        row_id = self.timeline_rows_tree.identify_row(getattr(event, "y", 0))
        if row_id:
            self._open_timeline_task_by_id(int(row_id))

    def _draw_timeline_row_grid(self, *, left_pad: int, top_pad: int, row_h: int, row_count: int, width: int) -> None:
        if not self.timeline_canvas:
            return
        line_color = self._theme_color("border", "#D8DDD8")
        for idx in range(row_count + 1):
            y = top_pad + idx * row_h
            self.timeline_canvas.create_line(left_pad, y, width, y, fill=line_color)

    def _draw_timeline_row(self, idx: int, row: dict[str, Any], *, min_date: date, ppd: int, left_pad: int, top_pad: int, row_h: int) -> None:
        if not self.timeline_canvas:
            return
        task_id = int(row.get("id", 0))
        start, end = self._task_timeline_bounds(row)
        y = top_pad + idx * row_h
        x0 = left_pad + max(0, (start - min_date).days) * ppd
        x1 = left_pad + (max(0, (end - min_date).days) + 1) * ppd
        tag = f"timeline_task_{task_id}"
        self.timeline_canvas.create_rectangle(x0, y + 6, x1, y + row_h - 8, fill=self._theme_color("accent", "#4F6B5A"), outline="", tags=(tag,))
        for pause in self.timeline_pauses_by_task_id.get(task_id, []):
            p_start = self._parse_iso_date(pause.get("date_start"))
            p_end = self._parse_iso_date(pause.get("date_end")) or date.today()
            if not p_start:
                continue
            if p_end < p_start:
                p_end = p_start
            px0 = left_pad + max(0, (p_start - min_date).days) * ppd
            px1 = left_pad + (max(0, (p_end - min_date).days) + 1) * ppd
            self.timeline_canvas.create_rectangle(px0, y + 12, px1, y + row_h - 14, fill=self._theme_color("warning", "#B07A2F"), outline="", tags=(tag,))
        self.timeline_canvas.tag_bind(tag, "<Double-1>", lambda _e, tid=task_id: self._open_timeline_task_by_id(tid))

    def _refresh_timeline(self) -> None:
        if "timeline_rows_tree" not in self.__dict__ or "timeline_canvas" not in self.__dict__:
            return
        if not self.timeline_rows_tree or not self.timeline_canvas:
            return
        rows_global = self._build_filtered_task_rows()
        rows = self._apply_timeline_slice(rows_global)

        self.timeline_full_text_by_task_id = {}
        self._timeline_hover_task_id = None
        self._hide_widget_tooltip()

        self.timeline_rows_tree.delete(*self.timeline_rows_tree.get_children())
        for row in rows:
            task_id = int(row.get("id", 0) or 0)
            full_description = str(row.get("description", "") or "")
            self.timeline_full_text_by_task_id[task_id] = full_description
            values = (
                row.get("id", ""),
                self._truncate_timeline_text(full_description),
                row.get("status", ""),
                row.get("executor_full_name", ""),
                row.get("date_start_work", "") or row.get("date_created", ""),
                row.get("date_done", "") or "-",
            )
            self.timeline_rows_tree.insert("", END, iid=str(row.get("id")), values=values)

        self.timeline_canvas.delete("all")
        if not rows:
            self.timeline_canvas.create_text(20, 20, anchor="nw", text="Нет данных для Timeline", fill=self._theme_color("text_muted", "#5F6B6D"))
            self.timeline_canvas.configure(scrollregion=(0, 0, 600, 120))
            return

        bounds = [self._task_timeline_bounds(r) for r in rows]
        min_date = min(s for s, _ in bounds)
        max_date = max(e for _, e in bounds)
        slice_bounds = self._timeline_slice_bounds(show_errors=False)
        if slice_bounds is not None:
            slice_start, slice_end = slice_bounds
            if slice_start:
                min_date = min(min_date, slice_start)
            if slice_end:
                max_date = max(max_date, slice_end)

        row_h = TIMELINE_ROW_HEIGHT
        left_pad = 20
        top_pad = 30
        ppd = self._draw_timeline_axis(min_date, max_date, left_pad, top_pad, row_h, len(rows))

        total_days = max(1, (max_date - min_date).days + 1)
        width = 40 + total_days * ppd
        self._draw_timeline_row_grid(left_pad=left_pad, top_pad=top_pad, row_h=row_h, row_count=len(rows), width=width)
        for idx, row in enumerate(rows):
            self._draw_timeline_row(idx, row, min_date=min_date, ppd=ppd, left_pad=left_pad, top_pad=top_pad, row_h=row_h)

        height = top_pad + len(rows) * row_h + 20
        self.timeline_canvas.configure(scrollregion=(0, 0, width, height))

    def _replace_analytics_filter_rows_from_context(self) -> None:
        if not hasattr(self, "analytics_rows_holder"):
            return
        for row in self.analytics_filter_rows:
            row.frame.destroy()
        self.analytics_filter_rows.clear()
        for cond in self.global_filter_context.rows:
            self._add_analytics_filter_row(
                field=cond.field or "status",
                op=cond.op or "==",
                value=cond.value,
                logic=cond.logic or "AND",
            )
        self.analytics_filter_visible = bool(self.global_filter_context.analytics_visible)
        if self.analytics_filter_visible:
            self.analytics_filter_panel.pack(fill="x", before=self.analytics_bottom_controls)
        else:
            self.analytics_filter_panel.pack_forget()

    def _compute_analytics_dataset(self, rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        today = date.today()
        stats: list[dict[str, Any]] = []
        for row in rows:
            task_id = int(row.get("id", 0))
            start = self._parse_iso_date(row.get("date_start_work")) or self._parse_iso_date(row.get("date_created")) or today
            end = self._parse_iso_date(row.get("date_done")) or today
            if end < start:
                end = start
            created = self._parse_iso_date(row.get("date_created")) or start
            pause_days = 0
            for pause in self.timeline_pauses_by_task_id.get(task_id, []):
                p_start = self._parse_iso_date(pause.get("date_start"))
                p_end = self._parse_iso_date(pause.get("date_end")) or today
                if not p_start:
                    continue
                if p_end < p_start:
                    p_end = p_start
                pause_days += (p_end - p_start).days + 1
            cycle_days = max(1, (end - start).days + 1)
            lead_days = max(1, (end - created).days + 1)
            stats.append({"row": row, "task_id": task_id, "start": start, "end": end, "cycle_days": cycle_days, "lead_days": lead_days, "pause_days": pause_days})

        charts: dict[str, list[dict[str, Any]]] = {}

        status_groups: dict[str, list[int]] = defaultdict(list)
        for st in stats:
            status_groups[str(st["row"].get("status", "")).strip() or "-"].append(st["task_id"])
        charts["status_distribution"] = [
            {"label": label, "value": len(ids), "row_ids": ids, "condition": {"field": "status", "op": "==", "value": label}}
            for label, ids in sorted(status_groups.items(), key=lambda kv: len(kv[1]), reverse=True)[:12]
        ]

        wip = {"Создана", "В работе", "Приостановлена"}
        wip_groups: dict[str, list[int]] = defaultdict(list)
        for st in stats:
            row = st["row"]
            if str(row.get("status")) in wip:
                wip_groups[str(row.get("executor_full_name") or "Не назначен")].append(st["task_id"])
        charts["wip_by_executor"] = [
            {"label": label, "value": len(ids), "row_ids": ids, "condition": {"field": "executor_full_name", "op": "==", "value": label}}
            for label, ids in sorted(wip_groups.items(), key=lambda kv: len(kv[1]), reverse=True)[:12]
        ]

        throughput: dict[str, list[int]] = defaultdict(list)
        throughput_ranges: dict[str, tuple[date, date]] = {}
        for st in stats:
            done = self._parse_iso_date(st["row"].get("date_done"))
            if not done:
                continue
            year, week, _ = done.isocalendar()
            key = f"{year}-W{week:02d}"
            throughput[key].append(st["task_id"])
            throughput_ranges[key] = (date.fromisocalendar(year, week, 1), date.fromisocalendar(year, week, 7))
        charts["throughput_by_week"] = [
            {
                "label": key,
                "value": len(ids),
                "row_ids": ids,
                "condition": {"field": "date_done", "op": "between", "value": f"{throughput_ranges[key][0].isoformat()},{throughput_ranges[key][1].isoformat()}"},
            }
            for key, ids in sorted(throughput.items())[-12:]
        ]

        by_project: dict[str, list[int]] = defaultdict(list)
        cycle_values: dict[str, list[int]] = defaultdict(list)
        for st in stats:
            label = str(st["row"].get("project_name") or f"Проект {st['row'].get('project_id', '')}")
            by_project[label].append(st["task_id"])
            cycle_values[label].append(int(st["cycle_days"]))
        charts["cycle_time_by_project"] = [
            {
                "label": label,
                "value": round(float(median(vals)), 2),
                "row_ids": by_project[label],
                "condition": {"field": "project_name", "op": "==", "value": label},
            }
            for label, vals in sorted(cycle_values.items(), key=lambda kv: median(kv[1]), reverse=True)[:12]
        ]

        by_pocket: dict[str, list[int]] = defaultdict(list)
        lead_values: dict[str, list[int]] = defaultdict(list)
        for st in stats:
            label = str(st["row"].get("pocket_name") or f"Карман {st['row'].get('pocket_id', '')}")
            by_pocket[label].append(st["task_id"])
            lead_values[label].append(int(st["lead_days"]))
        charts["lead_time_by_pocket"] = [
            {
                "label": label,
                "value": round(float(median(vals)), 2),
                "row_ids": by_pocket[label],
                "condition": {"field": "pocket_name", "op": "==", "value": label},
            }
            for label, vals in sorted(lead_values.items(), key=lambda kv: median(kv[1]), reverse=True)[:12]
        ]

        overdue_ids: list[int] = []
        for st in stats:
            deadline = self._parse_iso_date(st["row"].get("date_end"))
            if deadline and today > deadline and str(st["row"].get("status")) != "Завершена":
                overdue_ids.append(st["task_id"])
        charts["overdue_tasks"] = [{"label": "Просроченные", "value": len(overdue_ids), "row_ids": overdue_ids, "condition": {"field": "status", "op": "!=", "value": "Завершена"}}]

        pause_exec: dict[str, list[int]] = defaultdict(list)
        pause_vals: dict[str, list[float]] = defaultdict(list)
        for st in stats:
            label = str(st["row"].get("executor_full_name") or "Не назначен")
            ratio = (float(st["pause_days"]) / float(st["cycle_days"])) * 100.0
            pause_exec[label].append(st["task_id"])
            pause_vals[label].append(ratio)
        charts["pause_ratio_by_executor"] = [
            {
                "label": label,
                "value": round(sum(vals) / max(1, len(vals)), 2),
                "row_ids": pause_exec[label],
                "condition": {"field": "executor_full_name", "op": "==", "value": label},
            }
            for label, vals in sorted(pause_vals.items(), key=lambda kv: sum(kv[1]) / max(1, len(kv[1])), reverse=True)[:12]
        ]

        queue_items: list[dict[str, Any]] = []
        for st in stats:
            row = st["row"]
            if str(row.get("status")) == "Создана" and row.get("executor_user_id") is None:
                age = max(1, (today - (self._parse_iso_date(row.get("date_created")) or st["start"])).days + 1)
                queue_items.append({"label": f"#{st['task_id']}", "value": age, "row_ids": [st["task_id"]], "condition": {"field": "id", "op": "==", "value": str(st["task_id"])}})
        charts["queue_age"] = sorted(queue_items, key=lambda i: i["value"], reverse=True)[:12]
        return charts

    def _draw_analytics_charts(self, dataset: dict[str, list[dict[str, Any]]]) -> None:
        self.analytics_chart_dataset = dataset
        for key, canvas in self.analytics_charts.items():
            canvas.delete("all")
            items = dataset.get(key, [])
            if not items:
                canvas.create_text(10, 12, anchor="nw", text="Нет данных", fill=self._theme_color("text_muted", "#5F6B6D"))
                continue
            width = max(320, int(canvas.winfo_width() or 320))
            canvas.create_text(8, 8, anchor="nw", text="Срез", fill=self._theme_color("text_muted", "#5F6B6D"))
            canvas.create_text(width - 8, 8, anchor="ne", text="Значение", fill=self._theme_color("text_muted", "#5F6B6D"))
            canvas.create_line(8, 24, width - 8, 24, fill=self._theme_color("border", "#D8DDD8"))
            for idx, item in enumerate(items[:10]):
                y = 30 + idx * 15
                tag = f"a_{key}_{idx}"
                label = f"{idx + 1}. {str(item['label'])[:24]}"
                value = str(item["value"])
                canvas.create_text(8, y, anchor="nw", text=label, fill=self._theme_color("text_primary", "#1F2A2A"), tags=(tag,))
                canvas.create_text(width - 8, y, anchor="ne", text=value, fill=self._theme_color("accent", "#4F6B5A"), tags=(tag,))
                canvas.create_line(8, y + 13, width - 8, y + 13, fill=self._theme_color("border", "#D8DDD8"))
                tip = f"{item['label']}: {item['value']} (n={len(item.get('row_ids', []))})"
                canvas.tag_bind(tag, "<Enter>", lambda e, txt=tip: self._show_widget_tooltip(e, txt))
                canvas.tag_bind(tag, "<Leave>", self._hide_widget_tooltip)
                canvas.tag_bind(tag, "<Button-1>", lambda _e, mk=key, bi=idx: self._on_analytics_chart_click(mk, bi))

    def _on_analytics_chart_click(self, metric_key: str, bucket_index: int) -> None:
        data = getattr(self, "analytics_chart_dataset", {})
        items = data.get(metric_key, [])
        if bucket_index < 0 or bucket_index >= len(items):
            return
        bucket = items[bucket_index]
        self.analytics_selected_slice = {
            "metric_key": metric_key,
            "label": bucket.get("label", ""),
            "row_ids": list(bucket.get("row_ids", [])),
            "condition": bucket.get("condition", {}),
        }
        self._apply_analytics_drilldown_to_global_filter(self.analytics_selected_slice["condition"])

    def _apply_analytics_drilldown_to_global_filter(self, condition: dict[str, Any]) -> None:
        if not condition:
            return
        self.global_filter_context.rows = [row for row in self.global_filter_context.rows if row.tag != "analytics_drill"]
        self.global_filter_context.rows.append(
            FilterRowState(
                logic="AND",
                field=str(condition.get("field", "")),
                op=str(condition.get("op", "==")),
                value=str(condition.get("value", "")),
                tag="analytics_drill",
            )
        )
        self._apply_global_filter_context_to_zone("dashboard")
        self._apply_global_filter_context_to_zone("kanban")
        self._apply_global_filter_context_to_zone("timeline")
        self._apply_global_filter_context_to_zone("analytics")
        self._refresh_dashboard_top_table_from_filter_context()
        self._refresh_dashboard_bottom_table_from_selection_and_filter()
        self._refresh_kanban_board()
        self._refresh_timeline()
        self._refresh_analytics()
        self._refresh_global_filter_indicators()

    def _clear_analytics_drilldown(self) -> None:
        self.analytics_selected_slice = None
        self.global_filter_context.rows = [row for row in self.global_filter_context.rows if row.tag != "analytics_drill"]
        self._apply_global_filter_context_to_zone("dashboard")
        self._apply_global_filter_context_to_zone("kanban")
        self._apply_global_filter_context_to_zone("timeline")
        self._apply_global_filter_context_to_zone("analytics")
        self._refresh_dashboard_top_table_from_filter_context()
        self._refresh_dashboard_bottom_table_from_selection_and_filter()
        self._refresh_kanban_board()
        self._refresh_timeline()
        self._refresh_analytics()
        self._refresh_global_filter_indicators()

    def _refresh_analytics_details(self, rows_subset: list[dict[str, Any]]) -> None:
        if not self.analytics_details_tree:
            return
        self.analytics_details_tree.delete(*self.analytics_details_tree.get_children())
        for row in rows_subset[:300]:
            values = (
                row.get("id", ""),
                str(row.get("description", ""))[:120],
                row.get("status", ""),
                row.get("project_name", ""),
                row.get("pocket_name", ""),
                row.get("executor_full_name", ""),
                row.get("date_created", ""),
                row.get("date_done", "") or "-",
            )
            self.analytics_details_tree.insert("", END, iid=str(row.get("id")), values=values)

    def _on_analytics_details_double_click(self, event: object) -> None:
        if not self.analytics_details_tree:
            return
        row_id = self.analytics_details_tree.identify_row(getattr(event, "y", 0))
        if not row_id:
            return
        task = next((t for t in self.tasks_all if int(t.get("id", 0)) == int(row_id)), None)
        if task:
            self._open_task_form(mode="edit", task=task)

    def _refresh_analytics(self) -> None:
        if "analytics_charts" not in self.__dict__:
            return
        rows = self._build_filtered_task_rows()
        self.analytics_rows_cache = rows
        dataset = self._compute_analytics_dataset(rows)
        self._draw_analytics_charts(dataset)
        details_rows = rows
        if self.analytics_selected_slice:
            ids = {int(i) for i in self.analytics_selected_slice.get("row_ids", [])}
            details_rows = [r for r in rows if int(r.get("id", 0)) in ids]
            if hasattr(self, "analytics_clear_drill_btn"):
                self.analytics_clear_drill_btn.state(["!disabled"])
        else:
            if hasattr(self, "analytics_clear_drill_btn"):
                self.analytics_clear_drill_btn.state(["disabled"])
        self._refresh_analytics_details(details_rows)

    def _show_zone(self, name: str) -> None:
        self._hide_widget_tooltip()
        self.current_zone = name
        for frame in self.zones.values():
            frame.pack_forget()
        self.zones[name].pack(fill=BOTH, expand=True)
        if name == "dashboard":
            self._apply_global_filter_context_to_zone("dashboard")
            self._apply_filters()
        elif name == "kanban":
            self._apply_global_filter_context_to_zone("kanban")
            self._refresh_kanban_board()
        elif name == "timeline":
            self._apply_global_filter_context_to_zone("timeline")
            self._refresh_timeline()
            self._refresh_global_filter_indicators()
        elif name == "analytics":
            self._apply_global_filter_context_to_zone("analytics")
            self._refresh_analytics()
            self._refresh_global_filter_indicators()

    def _toggle_filter_panel(self) -> None:
        self.filter_visible = not self.filter_visible
        if self.filter_visible:
            self.filter_panel.pack(fill="x", before=self.bottom_controls)
        else:
            self.filter_panel.pack_forget()
        self._sync_global_filter_context_from_rows(
            self.filter_rows,
            zone="dashboard",
            preset_name=self.preset_var.get() if hasattr(self, "preset_var") else DEFAULT_PRESET_NAME,
            visible=self.filter_visible,
        )

    def _toggle_kanban_filter_panel(self) -> None:
        self.kanban_filter_visible = not self.kanban_filter_visible
        if self.kanban_filter_visible:
            self.kanban_filter_panel.pack(fill="x", before=self.kanban_bottom_controls)
        else:
            self.kanban_filter_panel.pack_forget()
        self._sync_global_filter_context_from_rows(
            self.kanban_filter_rows,
            zone="kanban",
            preset_name=self.kanban_preset_var.get() if hasattr(self, "kanban_preset_var") else DEFAULT_PRESET_NAME,
            visible=self.kanban_filter_visible,
        )

    def _serialize_filter_rows(self, rows: list[FilterRow]) -> list[dict[str, str]]:
        payload: list[dict[str, str]] = []
        for idx, row in enumerate(rows):
            payload.append(
                {
                    "logic": row.logic_var.get() if idx > 0 else "AND",
                    "field": row.field_var.get(),
                    "op": row.op_var.get(),
                    "value": row.value_var.get(),
                }
            )
        return payload

    def _row_states_from_ui_rows(self, rows: list[FilterRow]) -> list[FilterRowState]:
        states: list[FilterRowState] = []
        for idx, row in enumerate(rows):
            states.append(
                FilterRowState(
                    logic=row.logic_var.get() if idx > 0 else "AND",
                    field=row.field_var.get(),
                    op=row.op_var.get(),
                    value=row.value_var.get(),
                )
            )
        return states

    def _sync_global_filter_context_from_rows(
        self,
        rows: list[FilterRow],
        zone: str,
        *,
        preset_name: str | None = None,
        visible: bool | None = None,
    ) -> None:
        self.global_filter_context.rows = self._row_states_from_ui_rows(rows)
        if preset_name is not None:
            self.global_filter_context.preset_name = preset_name
        if visible is not None:
            if zone == "dashboard":
                self.global_filter_context.dashboard_visible = visible
            elif zone == "kanban":
                self.global_filter_context.kanban_visible = visible
            elif zone == "timeline":
                self.global_filter_context.timeline_visible = visible
            elif zone == "analytics":
                self.global_filter_context.analytics_visible = visible
        self._refresh_global_filter_indicators()

    def _build_effective_filter_rows(self) -> list[FilterRowState]:
        rows = list(self.global_filter_context.rows)
        if self.selected_project_id is not None:
            rows.append(
                FilterRowState(
                    logic="AND",
                    field="project_id",
                    op="==",
                    value=str(self.selected_project_id),
                    tag="selected",
                )
            )
        return rows

    def _build_filtered_task_rows(self) -> list[dict[str, Any]]:
        rows = [self._build_task_view(t) for t in self.tasks_all]
        return self._apply_global_filter_to_zone("global", rows)

    def _build_top_rows_from_filtered_tasks(self, filtered_tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        all_project_rows = self._build_project_view_rows(list(self.projects_by_id.values()))
        by_project_id = {int(r["project_id"]): r for r in all_project_rows}
        selected_project_ids = sorted({int(r["project_id"]) for r in filtered_tasks})
        return [by_project_id[pid] for pid in selected_project_ids if pid in by_project_id]

    def _augment_top_rows_with_empty_projects(self, top_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not self.show_projects_without_tasks_var.get():
            return top_rows
        all_rows = self._build_project_view_rows(list(self.projects_by_id.values()))
        filtered_project_rows = self._apply_project_table_filters(all_rows, self._build_effective_filter_rows())
        existing = {int(r["project_id"]) for r in top_rows}
        for row in filtered_project_rows:
            pid = int(row["project_id"])
            if pid not in existing:
                top_rows.append(row)
                existing.add(pid)
        return top_rows

    def _replace_dashboard_filter_rows_from_context(self) -> None:
        if not hasattr(self, "rows_holder"):
            return
        for row in self.filter_rows:
            row.frame.destroy()
        self.filter_rows.clear()
        for cond in self.global_filter_context.rows:
            self._add_filter_row(
                field=cond.field or "status",
                op=cond.op or "==",
                value=cond.value,
                logic=cond.logic or "AND",
            )
        self.filter_visible = bool(self.global_filter_context.dashboard_visible)
        if self.filter_visible:
            self.filter_panel.pack(fill="x", before=self.bottom_controls)
        else:
            self.filter_panel.pack_forget()

    def _replace_kanban_filter_rows_from_context(self) -> None:
        if not hasattr(self, "kanban_rows_holder"):
            return
        for row in self.kanban_filter_rows:
            row.frame.destroy()
        self.kanban_filter_rows.clear()
        for cond in self.global_filter_context.rows:
            self._add_kanban_filter_row(
                field=cond.field or "status",
                op=cond.op or "==",
                value=cond.value,
                logic=cond.logic or "AND",
            )
        self.kanban_filter_visible = bool(self.global_filter_context.kanban_visible)
        if self.kanban_filter_visible:
            self.kanban_filter_panel.pack(fill="x", before=self.kanban_bottom_controls)
        else:
            self.kanban_filter_panel.pack_forget()

    def _replace_timeline_filter_rows_from_context(self) -> None:
        if not hasattr(self, "timeline_rows_holder"):
            return
        for row in self.timeline_filter_rows:
            row.frame.destroy()
        self.timeline_filter_rows.clear()
        for cond in self.global_filter_context.rows:
            self._add_timeline_filter_row(
                field=cond.field or "status",
                op=cond.op or "==",
                value=cond.value,
                logic=cond.logic or "AND",
            )
        self.timeline_filter_visible = bool(self.global_filter_context.timeline_visible)
        if self.timeline_filter_visible:
            self.timeline_filter_panel.pack(fill="x", before=self.timeline_bottom_controls)
        else:
            self.timeline_filter_panel.pack_forget()

    def _apply_global_filter_context_to_zone(self, zone_name: str) -> None:
        if zone_name == "dashboard":
            self._replace_dashboard_filter_rows_from_context()
            if hasattr(self, "preset_var"):
                self.preset_var.set(self.global_filter_context.preset_name)
        elif zone_name == "kanban":
            self._replace_kanban_filter_rows_from_context()
            if hasattr(self, "kanban_preset_var"):
                self.kanban_preset_var.set(self.global_filter_context.preset_name)
        elif zone_name == "timeline":
            self._replace_timeline_filter_rows_from_context()
            if "timeline_preset_var" in self.__dict__:
                self.timeline_preset_var.set(self.global_filter_context.preset_name)
        elif zone_name == "analytics":
            self._replace_analytics_filter_rows_from_context()
            if "analytics_preset_var" in self.__dict__:
                self.analytics_preset_var.set(self.global_filter_context.preset_name)

    def _apply_global_filter_to_zone(self, zone_name: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        del zone_name  # reserved for timeline/analytics specific behavior
        result = list(rows)
        conditions = self._build_effective_filter_rows()
        for idx, cond in enumerate(conditions):
            field = (cond.field or "").strip()
            op = (cond.op or "").strip()
            raw = cond.value
            if not field or not op:
                continue
            logic = cond.logic if idx > 0 else "AND"
            source_rows = result if logic == "AND" else rows
            filtered = [r for r in source_rows if self._match_condition(r.get(field), op, raw)]
            if idx == 0 or logic == "AND":
                result = filtered
            else:
                ids = {int(r["id"]) for r in result}
                for item in filtered:
                    if int(item["id"]) not in ids:
                        result.append(item)
        return result

    def _format_filter_text_for_states(self, rows: list[FilterRowState]) -> str:
        parts: list[str] = []
        for idx, cond in enumerate(rows):
            field = cond.field.strip()
            op = cond.op.strip()
            value = cond.value.strip()
            if not field or not op:
                continue
            clause = f"{field} {op} {value}".strip()
            if cond.tag == "selected":
                clause = f"{clause} [selected]"
            elif cond.tag == "analytics_drill":
                clause = f"{clause} [drill]"
            if idx > 0:
                clause = f"{cond.logic} {clause}"
            parts.append(clause)
        if not parts:
            return "Фильтр пуст"
        return " ".join(parts)

    def _refresh_global_filter_indicators(self) -> None:
        full_text = self._format_filter_text_for_states(self._build_effective_filter_rows())
        short_text = full_text if len(full_text) <= 100 else f"{full_text[:100].rstrip()}..."
        self.global_filter_context.summary_full = full_text
        self.global_filter_context.summary_short = short_text
        self._filter_summary_full_text = full_text
        self._kanban_filter_summary_full_text = full_text
        self.filter_summary_var.set(short_text)
        self.kanban_filter_summary_var.set(short_text)
        if hasattr(self, "timeline_filter_summary_var"):
            self.timeline_filter_summary_var.set(short_text)
        if hasattr(self, "analytics_filter_summary_var"):
            self.analytics_filter_summary_var.set(short_text)

    def _group_pauses_by_task_id(self, pauses: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
        grouped: dict[int, list[dict[str, Any]]] = {}
        for pause in pauses:
            task_id = int(pause.get("task_id", 0))
            grouped.setdefault(task_id, []).append(pause)
        return grouped

    def _load_dashboard_data(self) -> None:
        try:
            if self.session_user is None:
                self.session_user = self.api.get_session_user()
                role = str(self.session_user.get("role", "executor"))
                full_name = self.session_user.get("full_name") or self.system_login
                self.session_var.set(
                    f"{full_name} ({role})"
                )
                style = ttk.Style(self)
                style.configure("Session.TLabel", foreground=self.role_colors.get(role, self.role_colors["executor"]))
            users = self.api.list_users()
            pockets = self.api.list_pockets()
            projects = self.api.list_projects()
            tasks = self.api.list_tasks()
            pauses = self.api.list_task_pauses()
        except ApiClientError as exc:
            messagebox.showerror(
                "Ошибка API/аутентификации",
                (
                    f"{exc}\n\n"
                    "Проверьте, что системный логин существует в users и активен.\n"
                    "Текущий login: "
                    f"{self.system_login}"
                ),
            )
            return
        self.users_by_id = {int(u["id"]): u for u in users}
        self.pockets_by_id = {int(p["id"]): p for p in pockets}
        self.projects_by_id = {int(p["id"]): p for p in projects}
        self.tasks_all = tasks
        self.timeline_pauses_by_task_id = self._group_pauses_by_task_id(pauses)
        self._apply_filters()
        self._refresh_kanban_board()
        self._refresh_timeline()
        self._refresh_analytics()

    def _on_session_click(self, _: object) -> None:
        if not self.session_user:
            messagebox.showinfo("Сеанс", "Данные сессии еще не загружены.")
            return
        self._open_session_user_card()

    def _open_session_user_card(self) -> None:
        if not self.session_user:
            return
        w = self._create_popup(self)
        w.title("Карточка пользователя")
        w.geometry("420x220")
        full_name = self.session_user.get("full_name", "")
        login = self.session_user.get("login", "")
        role = self.session_user.get("role", "")
        text = (
            f"ФИО: {full_name}\n"
            f"Логин: {login}\n"
            f"Роль: {role}\n"
        )
        body = ttk.Frame(w, style="Surface.TFrame", padding=(16, 16))
        body.pack(fill=BOTH, expand=True)
        style = ttk.Style(self)
        style.configure("UserCard.TLabel", foreground=self.role_colors.get(str(role), self.role_colors["executor"]))
        ttk.Label(body, text=text, justify=LEFT, style="UserCard.TLabel").pack(fill=BOTH, expand=True)

    def _create_popup(self, parent: Tk | Toplevel) -> Toplevel:
        w = Toplevel(parent)
        style = ttk.Style(self)
        bg = style.lookup("TFrame", "background") or "#ffffff"
        w.configure(bg=bg)
        self._apply_window_icon(w)
        return w

    def _apply_window_icon(self, window: Tk | Toplevel) -> None:
        icon_file = _app_icon_file()
        if not os.path.exists(icon_file):
            return
        try:
            window.iconbitmap(icon_file)
        except Exception:
            try:
                self._window_logo_image = PhotoImage(file=icon_file)
                window.iconphoto(True, self._window_logo_image)
            except Exception:
                return

    def _can_manage_pockets(self) -> bool:
        if not self.session_user:
            return False
        role = str(self.session_user.get("role", "executor"))
        return role in {"admin", "head", "teamlead", "curator"}

    def _can_create_pockets(self) -> bool:
        if not self.session_user:
            return False
        role = str(self.session_user.get("role", "executor"))
        return role in {"admin", "head", "curator"}

    def _status_filter_to_api(self) -> str | None:
        ui_value = self.pocket_status_filter_var.get()
        if ui_value == "Активные":
            return "Запущен"
        if ui_value == "Архив":
            return "Завершён"
        return None

    def _open_pockets_window(self) -> None:
        if self.session_user is None:
            self._load_dashboard_data()
        if self.pocket_window and self.pocket_window.winfo_exists():
            self.pocket_window.lift()
            self.pocket_window.focus_force()
            return

        w = self._create_popup(self)
        w.title("Справочник: Карманы")
        w.geometry("1080x560")
        self.pocket_window = w
        w.protocol("WM_DELETE_WINDOW", self._close_pockets_window)

        top_bar = ttk.Frame(w, padding=(10, 10))
        top_bar.pack(fill="x")
        ttk.Label(top_bar, text="Показать:").pack(side=LEFT)
        status_combo = ttk.Combobox(
            top_bar,
            textvariable=self.pocket_status_filter_var,
            values=["Активные", "Архив", "Все"],
            state="readonly",
            width=14,
        )
        status_combo.pack(side=LEFT, padx=6)
        status_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_pockets_table())
        self._mk_button(top_bar, "Обновить", self._refresh_pockets_table).pack(side=LEFT, padx=4)
        self._mk_button(top_bar, "Закрыть", self._close_pockets_window).pack(side=RIGHT, padx=2)

        table_frame = ttk.Frame(w, padding=(10, 0))
        table_frame.pack(fill=BOTH, expand=True)
        cols = ("id", "name", "status", "date_start", "date_end", "owner", "department")
        self.pocket_tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for col in cols:
            self.pocket_tree.heading(col, text=POCKET_COLUMN_TITLES.get(col, col))
            self.pocket_tree.column(col, width=130, anchor="w")
        self.pocket_tree.column("id", width=70, anchor="center")
        self.pocket_tree.column("status", width=120, anchor="center")
        self.pocket_tree.pack(fill=BOTH, expand=True)
        self.pocket_tree.bind("<Double-1>", lambda _e: self._open_pocket_form_edit())

        actions = ttk.Frame(w, padding=(10, 10))
        actions.pack(fill="x")
        create_btn = self._mk_button(actions, "Создать", self._open_pocket_form_create)
        create_btn.pack(side=LEFT, padx=2)
        edit_btn = self._mk_button(actions, "Изменить", self._open_pocket_form_edit)
        edit_btn.pack(side=LEFT, padx=2)
        archive_btn = self._mk_button(actions, "В архив", self._archive_selected_pocket)
        archive_btn.pack(side=LEFT, padx=2)
        ttk.Label(actions, text="Удаление не поддерживается. Используйте архив.", style="Surface.TLabel").pack(side=LEFT, padx=14)

        can_create = self._can_create_pockets()
        can_manage = self._can_manage_pockets()
        if not can_create:
            create_btn.state(["disabled"])
        if not can_manage:
            edit_btn.state(["disabled"])
            archive_btn.state(["disabled"])

        self._refresh_pockets_table()

    def _close_pockets_window(self) -> None:
        if self.pocket_window and self.pocket_window.winfo_exists():
            self.pocket_window.destroy()
        self.pocket_window = None
        self.pocket_tree = None

    def _refresh_pockets_table(self) -> None:
        if not self.pocket_tree:
            return
        try:
            self.pocket_users_by_id = {int(u["id"]): u for u in self.api.list_users()}
            pockets = self.api.list_pockets(status=self._status_filter_to_api())
            all_pockets = self.api.list_pockets()
        except ApiClientError as exc:
            messagebox.showerror("Ошибка API", f"Не удалось загрузить карманы.\n{exc}", parent=self.pocket_window)
            return
        self.department_catalog = sorted({str(p.get("department", "")).strip() for p in all_pockets if p.get("department")})

        self.pocket_tree.delete(*self.pocket_tree.get_children())
        rows_for_width: list[tuple[Any, ...]] = []
        for pocket in pockets:
            owner_name = self.pocket_users_by_id.get(int(pocket["owner_user_id"]), {}).get("full_name", "")
            values = (
                pocket.get("id", ""),
                pocket.get("name", ""),
                pocket.get("status", ""),
                pocket.get("date_start", ""),
                pocket.get("date_end", "") or "-",
                owner_name,
                pocket.get("department", ""),
            )
            rows_for_width.append(values)
            self.pocket_tree.insert("", END, iid=str(pocket["id"]), values=values)
        self._autosize_tree_columns(
            self.pocket_tree,
            ("id", "name", "status", "date_start", "date_end", "owner", "department"),
            rows_for_width,
            min_width=90,
            max_width_overrides={"name": 320, "owner": 260, "department": 180},
        )

    def _selected_pocket_id(self) -> int | None:
        if not self.pocket_tree:
            return None
        selected = self.pocket_tree.selection()
        if not selected:
            return None
        return int(selected[0])

    def _open_pocket_form_create(self) -> None:
        self._open_pocket_form(mode="create", pocket=None)

    def _open_pocket_form_edit(self) -> None:
        pocket_id = self._selected_pocket_id()
        if pocket_id is None:
            messagebox.showinfo("Карманы", "Выберите строку кармана.", parent=self.pocket_window)
            return
        try:
            pocket = next((p for p in self.api.list_pockets() if int(p["id"]) == pocket_id), None)
        except ApiClientError as exc:
            messagebox.showerror("Ошибка API", f"Не удалось загрузить карточку кармана.\n{exc}", parent=self.pocket_window)
            return
        if not pocket:
            messagebox.showerror("Карманы", "Карман не найден.", parent=self.pocket_window)
            return
        self._open_pocket_form(mode="edit", pocket=pocket)

    def _open_pocket_form(self, *, mode: str, pocket: dict[str, Any] | None) -> None:
        if mode == "create":
            if not self._can_create_pockets():
                messagebox.showwarning(
                    "???????????? ????",
                    "Создание доступно для роли куратор и выше.",
                    parent=self.pocket_window,
                )
                return
        elif not self._can_manage_pockets():
            messagebox.showwarning(
                "???????????? ????",
                "Изменение и архивация доступны для ролей куратор, head, admin.",
                parent=self.pocket_window,
            )
            return

        if not self.pocket_users_by_id:
            try:
                raw_users = self.api.list_users()
                self.pocket_users_by_id = {int(u["id"]): u for u in raw_users if int(u.get("is_active", 1)) == 1}
                if pocket:
                    current_owner = int(pocket.get("owner_user_id", 0))
                    missing = next((u for u in raw_users if int(u["id"]) == current_owner), None)
                    if missing:
                        self.pocket_users_by_id[current_owner] = missing
            except ApiClientError as exc:
                messagebox.showerror("Ошибка API", f"Не удалось загрузить пользователей.\n{exc}", parent=self.pocket_window)
                return
        if not self.department_catalog:
            try:
                all_pockets = self.api.list_pockets()
                self.department_catalog = sorted(
                    {str(p.get("department", "")).strip() for p in all_pockets if p.get("department")}
                )
            except ApiClientError:
                self.department_catalog = []

        w = self._create_popup(self.pocket_window or self)
        w.title("Новый карман" if mode == "create" else f"Изменить карман #{pocket.get('id') if pocket else ''}")
        w.geometry("620x420")

        frame = ttk.Frame(w, padding=(14, 14))
        frame.pack(fill=BOTH, expand=True)

        name_var = StringVar(value=(pocket.get("name", "") if pocket else ""))
        date_start_var = StringVar(value=(pocket.get("date_start", "") if pocket else date.today().isoformat()))
        date_end_var = StringVar(value=(pocket.get("date_end", "") if pocket and pocket.get("date_end") else ""))
        dept_var = StringVar(value=(pocket.get("department", "") if pocket else (self.department_catalog[0] if self.department_catalog else "")))
        status_var = StringVar(value=(pocket.get("status", "Запущен") if pocket else "Запущен"))

        owner_items = [
            (int(u["id"]), str(u.get("full_name", "")))
            for _, u in sorted(self.pocket_users_by_id.items(), key=lambda item: str(item[1].get("full_name", "")))
        ]
        owner_label_to_id = {f"{full_name} (id:{uid})": uid for uid, full_name in owner_items}
        owner_options = list(owner_label_to_id.keys())
        owner_default = owner_options[0] if owner_options else ""
        if pocket:
            owner_id = int(pocket.get("owner_user_id"))
            owner = self.pocket_users_by_id.get(owner_id)
            owner_full_name = owner.get("full_name", "") if owner else ""
            owner_default = f"{owner_full_name} (id:{owner_id})"
        owner_var = StringVar(value=owner_default)

        basic = ttk.LabelFrame(frame, text="Основные данные", padding=(10, 10))
        basic.pack(fill="x")
        basic.columnconfigure(1, weight=1)
        ttk.Label(basic, text="Наименование *").grid(row=0, column=0, sticky="w", pady=4, padx=(0, 8))
        ttk.Entry(basic, textvariable=name_var).grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Label(basic, text="Ответственный *").grid(row=1, column=0, sticky="w", pady=4, padx=(0, 8))
        owner_combo = ttk.Combobox(basic, textvariable=owner_var, values=owner_options, state="readonly")
        owner_combo.grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Label(basic, text="Подразделение *").grid(row=2, column=0, sticky="w", pady=4, padx=(0, 8))
        dept_combo = ttk.Combobox(basic, textvariable=dept_var, values=self.department_catalog, state="normal")
        dept_combo.grid(row=2, column=1, sticky="ew", pady=4)

        dates = ttk.LabelFrame(frame, text="Сроки и статус", padding=(10, 10))
        dates.pack(fill="x", pady=(10, 0))
        dates.columnconfigure(1, weight=1)
        ttk.Label(dates, text="Дата начала *").grid(row=0, column=0, sticky="w", pady=4, padx=(0, 8))
        start_wrap = ttk.Frame(dates)
        start_wrap.grid(row=0, column=1, sticky="ew", pady=4)
        start_wrap.columnconfigure(0, weight=1)
        ttk.Entry(start_wrap, textvariable=date_start_var).grid(row=0, column=0, sticky="ew")
        self._add_date_picker_button(start_wrap, date_start_var).grid(row=0, column=1, padx=(6, 0))

        ttk.Label(dates, text="Дата окончания").grid(row=1, column=0, sticky="w", pady=4, padx=(0, 8))
        end_wrap = ttk.Frame(dates)
        end_wrap.grid(row=1, column=1, sticky="ew", pady=4)
        end_wrap.columnconfigure(0, weight=1)
        ttk.Entry(end_wrap, textvariable=date_end_var).grid(row=0, column=0, sticky="ew")
        self._add_date_picker_button(end_wrap, date_end_var).grid(row=0, column=1, padx=(6, 0))

        if mode == "edit":
            ttk.Label(dates, text="Статус").grid(row=2, column=0, sticky="w", pady=4, padx=(0, 8))
            status_combo = ttk.Combobox(dates, textvariable=status_var, values=["Запущен", "Завершён"], state="readonly")
            status_combo.grid(row=2, column=1, sticky="ew", pady=4)

        hint = ttk.Label(frame, text="Подсказка: даты в формате YYYY-MM-DD. Кнопка 📅 открывает календарь.")
        hint.pack(anchor="w", pady=(8, 0))

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(16, 0))

        def save_form() -> None:
            name = name_var.get().strip()
            ds = date_start_var.get().strip()
            de = date_end_var.get().strip()
            dept = dept_var.get().strip()
            owner_selected = owner_var.get().strip()
            if not name:
                messagebox.showerror("Валидация", "Поле 'Наименование' обязательно.", parent=w)
                return
            if not dept:
                messagebox.showerror("Валидация", "Поле 'Подразделение' обязательно.", parent=w)
                return
            if not owner_selected:
                messagebox.showerror("Валидация", "Выберите ответственного из списка.", parent=w)
                return
            owner_id = owner_label_to_id.get(owner_selected)
            if owner_id is None:
                messagebox.showerror("Валидация", "Некорректный ответственный.", parent=w)
                return
            if owner_id not in self.pocket_users_by_id:
                messagebox.showerror("Валидация", "Выбранный ответственный не найден.", parent=w)
                return
            try:
                d_start = datetime.strptime(ds, "%Y-%m-%d").date()
            except ValueError:
                messagebox.showerror("Валидация", "Неверный формат даты начала.", parent=w)
                return
            d_end: date | None = None
            if de:
                try:
                    d_end = datetime.strptime(de, "%Y-%m-%d").date()
                except ValueError:
                    messagebox.showerror("Валидация", "Неверный формат даты окончания.", parent=w)
                    return
                if d_end < d_start:
                    messagebox.showerror("Валидация", "Дата окончания не может быть раньше даты начала.", parent=w)
                    return

            payload: dict[str, Any] = {
                "name": name,
                "date_start": d_start.isoformat(),
                "date_end": d_end.isoformat() if d_end else None,
                "owner_user_id": owner_id,
                "department": dept,
            }
            if mode == "create":
                payload["status"] = "Запущен"
            else:
                payload["status"] = status_var.get().strip() or "Запущен"

            try:
                if mode == "create":
                    self.api.create_pocket(payload)
                else:
                    assert pocket is not None
                    self.api.update_pocket(int(pocket["id"]), payload)
            except ApiClientError as exc:
                messagebox.showerror("Ошибка API", f"Сохранить не удалось.\n{exc}", parent=w)
                return

            w.destroy()
            self._refresh_pockets_table()
            self._load_dashboard_data()

        self._mk_button(buttons, "Сохранить", save_form).pack(side=LEFT)
        self._mk_button(buttons, "Отмена", w.destroy).pack(side=LEFT, padx=6)

    def _add_date_picker_button(self, parent: ttk.Frame, target_var: StringVar) -> ttk.Button:
        return self._mk_button(parent, "📅", lambda: self._open_calendar_popup(target_var), width=3)

    def _open_calendar_popup(self, target_var: StringVar) -> None:
        if Calendar is None:
            messagebox.showinfo(
                "Календарь недоступен",
                "Установите пакет 'tkcalendar' для выбора даты из календаря.\nСейчас используйте ручной ввод.",
                parent=self,
            )
            return
        current_value = target_var.get().strip()
        selected_date = date.today()
        if current_value:
            try:
                selected_date = datetime.strptime(current_value, "%Y-%m-%d").date()
            except ValueError:
                selected_date = date.today()

        w = self._create_popup(self)
        w.title("Выбор даты")
        w.geometry("280x280")
        body = ttk.Frame(w, padding=(8, 8))
        body.pack(fill=BOTH, expand=True)
        cal = Calendar(body, selectmode="day", year=selected_date.year, month=selected_date.month, day=selected_date.day)
        cal.pack(fill=BOTH, expand=True)

        actions = ttk.Frame(body)
        actions.pack(fill="x", pady=(8, 0))

        def apply_selected() -> None:
            target_var.set(cal.selection_get().isoformat())
            w.destroy()

        self._mk_button(actions, "Выбрать", apply_selected).pack(side=LEFT)
        self._mk_button(actions, "Отмена", w.destroy).pack(side=LEFT, padx=6)

    def _archive_selected_pocket(self) -> None:
        if not self._can_manage_pockets():
            messagebox.showwarning("???????????? ????", "???????? ??? ????? ???????, head, admin.", parent=self.pocket_window)
            return
        pocket_id = self._selected_pocket_id()
        if pocket_id is None:
            messagebox.showinfo("Карманы", "Выберите строку кармана.", parent=self.pocket_window)
            return
        current_row = self.pocket_tree.item(str(pocket_id), "values") if self.pocket_tree else ()
        if len(current_row) >= 3 and str(current_row[2]) == "Завершён":
            messagebox.showinfo("Карманы", "Карман уже находится в архиве.", parent=self.pocket_window)
            return
        if not messagebox.askyesno("Подтверждение", "Перевести выбранный карман в архив?", parent=self.pocket_window):
            return
        try:
            self.api.update_pocket(pocket_id, {"status": "Завершён"})
        except ApiClientError as exc:
            messagebox.showerror("Ошибка API", f"Архивация не удалась.\n{exc}", parent=self.pocket_window)
            return
        self._refresh_pockets_table()
        self._load_dashboard_data()

    def _project_status_filter_to_api(self) -> str | None:
        ui_value = self.project_status_filter_var.get()
        if ui_value == "Активные":
            return "Активен"
        if ui_value == "Архив":
            return "Завершён"
        return None

    def _open_projects_window(self) -> None:
        if self.project_window and self.project_window.winfo_exists():
            self.project_window.lift()
            self.project_window.focus_force()
            self._refresh_projects_table()
            return

        w = self._create_popup(self)
        w.title("Справочник: Проекты")
        w.geometry("1260x620")
        self.project_window = w
        w.protocol("WM_DELETE_WINDOW", self._close_projects_window)

        top_bar = ttk.Frame(w, padding=(10, 10))
        top_bar.pack(fill="x")
        ttk.Label(top_bar, text="Показать:").pack(side=LEFT, padx=(0, 4))
        status_combo = ttk.Combobox(
            top_bar,
            textvariable=self.project_status_filter_var,
            values=["Активные", "Архив", "Все"],
            state="readonly",
            width=14,
        )
        status_combo.pack(side=LEFT)
        status_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_projects_table())
        self._mk_button(top_bar, "Обновить", self._refresh_projects_table).pack(side=LEFT, padx=6)
        self._mk_button(top_bar, "Закрыть", self._close_projects_window).pack(side=RIGHT)

        table_frame = ttk.Frame(w, padding=(10, 0))
        table_frame.pack(fill=BOTH, expand=True)
        cols = (
            "id",
            "pocket_id",
            "pocket_name",
            "name",
            "project_code",
            "status",
            "date_start",
            "date_end",
            "curator_business",
            "curator_it",
        )
        self.project_tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for col in cols:
            self.project_tree.heading(col, text=PROJECT_COLUMN_TITLES.get(col, col))
            self.project_tree.column(col, width=130, anchor="w")
        self.project_tree.column("id", width=70, anchor="center")
        self.project_tree.column("pocket_id", width=90, anchor="center")
        self.project_tree.column("status", width=120, anchor="center")
        self.project_tree.pack(fill=BOTH, expand=True)
        self.project_tree.bind("<Double-1>", lambda _e: self._open_project_form_edit())

        actions = ttk.Frame(w, padding=(10, 10))
        actions.pack(fill="x")
        self._mk_button(actions, "Создать", self._open_project_form_create).pack(side=LEFT, padx=2)
        self._mk_button(actions, "Изменить", self._open_project_form_edit).pack(side=LEFT, padx=2)
        self._mk_button(actions, "В архив", self._archive_selected_project).pack(side=LEFT, padx=2)

        if not self._can_manage_pockets():
            for child in actions.winfo_children():
                if isinstance(child, ttk.Button):
                    child.state(["disabled"])

        self._refresh_projects_table()

    def _close_projects_window(self) -> None:
        if self.project_window and self.project_window.winfo_exists():
            self.project_window.destroy()
        self.project_window = None
        self.project_tree = None

    def _refresh_projects_table(self) -> None:
        if not self.project_tree:
            return
        try:
            users = {int(u["id"]): u for u in self.api.list_users()}
            pockets = {int(p["id"]): p for p in self.api.list_pockets()}
            projects = self.api.list_projects(status=self._project_status_filter_to_api())
        except ApiClientError as exc:
            messagebox.showerror("Ошибка API", f"Не удалось загрузить проекты.\n{exc}", parent=self.project_window)
            return
        self.project_tree.delete(*self.project_tree.get_children())
        rows_for_width: list[tuple[Any, ...]] = []
        for project in projects:
            curator_business = users.get(int(project.get("curator_business_user_id", 0)), {}).get("full_name", "")
            curator_it = users.get(int(project.get("curator_it_user_id", 0)), {}).get("full_name", "")
            values = (
                project.get("id", ""),
                project.get("pocket_id", ""),
                pockets.get(int(project.get("pocket_id", 0)), {}).get("name", ""),
                project.get("name", ""),
                project.get("project_code", "") or "",
                project.get("status", ""),
                project.get("date_start", ""),
                project.get("date_end", "") or "-",
                curator_business,
                curator_it,
            )
            rows_for_width.append(values)
            self.project_tree.insert("", END, iid=str(project["id"]), values=values)
        self._autosize_tree_columns(
            self.project_tree,
            ("id", "pocket_id", "pocket_name", "name", "project_code", "status", "date_start", "date_end", "curator_business", "curator_it"),
            rows_for_width,
            min_width=90,
            max_width_overrides={
                "pocket_name": 220,
                "name": 320,
                "project_code": 180,
                "curator_business": 220,
                "curator_it": 220,
            },
        )

    def _selected_project_id(self) -> int | None:
        if not self.project_tree:
            return None
        selected = self.project_tree.selection()
        if not selected:
            return None
        return int(selected[0])

    def _open_project_form_create(self) -> None:
        self._open_project_form(mode="create", project=None)

    def _open_project_form_edit(self) -> None:
        project_id = self._selected_project_id()
        if project_id is None:
            messagebox.showinfo("Проекты", "Выберите проект.", parent=self.project_window)
            return
        try:
            projects = self.api.list_projects()
        except ApiClientError as exc:
            messagebox.showerror("Ошибка API", f"Не удалось загрузить проект.\n{exc}", parent=self.project_window)
            return
        project = next((p for p in projects if int(p["id"]) == project_id), None)
        if not project:
            messagebox.showerror("Проекты", "Проект не найден.", parent=self.project_window)
            return
        self._open_project_form(mode="edit", project=project)

    def _open_project_form(self, *, mode: str, project: dict[str, Any] | None) -> None:
        if not self._can_manage_pockets():
            messagebox.showwarning("???????????? ????", "???????? ??? ????? ???????, head, admin.", parent=self.project_window)
            return
        try:
            raw_users = self.api.list_users()
            users = {int(u["id"]): u for u in raw_users if int(u.get("is_active", 1)) == 1}
            pockets = self.api.list_pockets()
            if project:
                cb = int(project.get("curator_business_user_id", 0))
                ci = int(project.get("curator_it_user_id", 0))
                for uid in (cb, ci):
                    if uid not in users:
                        found = next((u for u in raw_users if int(u["id"]) == uid), None)
                        if found:
                            users[uid] = found
        except ApiClientError as exc:
            messagebox.showerror("Ошибка API", f"Не удалось загрузить справочники.\n{exc}", parent=self.project_window)
            return

        w = self._create_popup(self.project_window or self)
        w.title("Новый проект" if mode == "create" else f"Изменить проект #{project.get('id') if project else ''}")
        w.geometry("700x560")
        frame = ttk.Frame(w, padding=(14, 14))
        frame.pack(fill=BOTH, expand=True)

        name_var = StringVar(value=(project.get("name", "") if project else ""))
        project_code_var = StringVar(value=(project.get("project_code", "") if project else ""))
        date_start_var = StringVar(value=(project.get("date_start", "") if project else date.today().isoformat()))
        date_end_var = StringVar(value=(project.get("date_end", "") if project and project.get("date_end") else ""))
        status_var = StringVar(value=(project.get("status", "Активен") if project else "Активен"))
        pocket_items = [(int(p["id"]), str(p.get("name", ""))) for p in pockets]
        pocket_label_to_id = {f"{name} (id:{pid})": pid for pid, name in pocket_items}
        pocket_options = list(pocket_label_to_id.keys())
        pocket_var = StringVar(value=pocket_options[0] if pocket_options else "")
        if project:
            pid = int(project.get("pocket_id", 0))
            pname = next((name for id_value, name in pocket_items if id_value == pid), "")
            pocket_var.set(f"{pname} (id:{pid})")

        user_items = [(int(u["id"]), str(u.get("full_name", ""))) for _, u in sorted(users.items(), key=lambda item: str(item[1].get("full_name", "")))]
        label_to_id = {f"{full_name} (id:{uid})": uid for uid, full_name in user_items}
        user_options = list(label_to_id.keys())

        curator_business_var = StringVar(value=user_options[0] if user_options else "")
        curator_it_var = StringVar(value=user_options[0] if user_options else "")
        if project:
            business_id = int(project.get("curator_business_user_id", 0))
            it_id = int(project.get("curator_it_user_id", 0))
            business_name = users.get(business_id, {}).get("full_name", "")
            it_name = users.get(it_id, {}).get("full_name", "")
            curator_business_var.set(f"{business_name} (id:{business_id})")
            curator_it_var.set(f"{it_name} (id:{it_id})")

        basic = ttk.LabelFrame(frame, text="Основные данные", padding=(10, 10))
        basic.pack(fill="x")
        basic.columnconfigure(1, weight=1)
        ttk.Label(basic, text="Наименование *").grid(row=0, column=0, sticky="w", pady=4, padx=(0, 8))
        ttk.Entry(basic, textvariable=name_var).grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Label(basic, text="Код проекта").grid(row=1, column=0, sticky="w", pady=4, padx=(0, 8))
        ttk.Entry(basic, textvariable=project_code_var).grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Label(basic, text="Карман *").grid(row=2, column=0, sticky="w", pady=4, padx=(0, 8))
        ttk.Combobox(basic, textvariable=pocket_var, values=pocket_options, state="readonly").grid(row=2, column=1, sticky="ew", pady=4)
        ttk.Label(basic, text="Куратор бизнес *").grid(row=3, column=0, sticky="w", pady=4, padx=(0, 8))
        ttk.Combobox(basic, textvariable=curator_business_var, values=user_options, state="readonly").grid(row=3, column=1, sticky="ew", pady=4)
        ttk.Label(basic, text="Куратор ИТ *").grid(row=4, column=0, sticky="w", pady=4, padx=(0, 8))
        ttk.Combobox(basic, textvariable=curator_it_var, values=user_options, state="readonly").grid(row=4, column=1, sticky="ew", pady=4)

        dates = ttk.LabelFrame(frame, text="Сроки и статус", padding=(10, 10))
        dates.pack(fill="x", pady=(10, 0))
        dates.columnconfigure(1, weight=1)
        ttk.Label(dates, text="Дата начала *").grid(row=0, column=0, sticky="w", pady=4, padx=(0, 8))
        start_wrap = ttk.Frame(dates)
        start_wrap.grid(row=0, column=1, sticky="ew", pady=4)
        start_wrap.columnconfigure(0, weight=1)
        ttk.Entry(start_wrap, textvariable=date_start_var).grid(row=0, column=0, sticky="ew")
        self._add_date_picker_button(start_wrap, date_start_var).grid(row=0, column=1, padx=(6, 0))
        ttk.Label(dates, text="Дата окончания").grid(row=1, column=0, sticky="w", pady=4, padx=(0, 8))
        end_wrap = ttk.Frame(dates)
        end_wrap.grid(row=1, column=1, sticky="ew", pady=4)
        end_wrap.columnconfigure(0, weight=1)
        ttk.Entry(end_wrap, textvariable=date_end_var).grid(row=0, column=0, sticky="ew")
        self._add_date_picker_button(end_wrap, date_end_var).grid(row=0, column=1, padx=(6, 0))
        if mode == "edit":
            ttk.Label(dates, text="Статус").grid(row=2, column=0, sticky="w", pady=4, padx=(0, 8))
            ttk.Combobox(dates, textvariable=status_var, values=["Активен", "Завершён"], state="readonly").grid(row=2, column=1, sticky="ew", pady=4)

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(16, 0))

        def save_form() -> None:
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Валидация", "Поле 'Наименование' обязательно.", parent=w)
                return
            try:
                ds = datetime.strptime(date_start_var.get().strip(), "%Y-%m-%d").date()
            except ValueError:
                messagebox.showerror("Валидация", "Неверный формат даты начала.", parent=w)
                return
            de: date | None = None
            if date_end_var.get().strip():
                try:
                    de = datetime.strptime(date_end_var.get().strip(), "%Y-%m-%d").date()
                except ValueError:
                    messagebox.showerror("Валидация", "Неверный формат даты окончания.", parent=w)
                    return
                if de < ds:
                    messagebox.showerror("Валидация", "Дата окончания не может быть раньше даты начала.", parent=w)
                    return
            business_id = label_to_id.get(curator_business_var.get().strip())
            it_id = label_to_id.get(curator_it_var.get().strip())
            if business_id is None or it_id is None:
                messagebox.showerror("Валидация", "Выберите кураторов из списка.", parent=w)
                return
            pocket_id = pocket_label_to_id.get(pocket_var.get().strip())
            if pocket_id is None:
                messagebox.showerror("Валидация", "Выберите карман из списка.", parent=w)
                return

            payload: dict[str, Any] = {
                "name": name,
                "project_code": project_code_var.get().strip() or None,
                "pocket_id": pocket_id,
                "status": status_var.get().strip() or "Активен",
                "date_start": ds.isoformat(),
                "date_end": de.isoformat() if de else None,
                "curator_business_user_id": business_id,
                "curator_it_user_id": it_id,
            }
            try:
                if mode == "create":
                    self.api.create_project(payload)
                else:
                    assert project is not None
                    self.api.update_project(int(project["id"]), payload)
            except ApiClientError as exc:
                messagebox.showerror("Ошибка API", f"Сохранить проект не удалось.\n{exc}", parent=w)
                return
            w.destroy()
            self._refresh_projects_table()
            self._load_dashboard_data()

        self._mk_button(buttons, "Сохранить", save_form).pack(side=LEFT)
        self._mk_button(buttons, "Отмена", w.destroy).pack(side=LEFT, padx=6)

    def _archive_selected_project(self) -> None:
        if not self._can_manage_pockets():
            messagebox.showwarning("???????????? ????", "???????? ??? ????? ???????, head, admin.", parent=self.project_window)
            return
        project_id = self._selected_project_id()
        if project_id is None:
            messagebox.showinfo("Проекты", "Выберите проект.", parent=self.project_window)
            return
        row = self.project_tree.item(str(project_id), "values") if self.project_tree else ()
        if len(row) >= 3 and str(row[2]) == "Завершён":
            messagebox.showinfo("Проекты", "Проект уже в архиве.", parent=self.project_window)
            return
        if not messagebox.askyesno("Подтверждение", "Перевести проект в архив?", parent=self.project_window):
            return
        try:
            self.api.update_project(project_id, {"status": "Завершён"})
        except ApiClientError as exc:
            messagebox.showerror("Ошибка API", f"Архивация проекта не удалась.\n{exc}", parent=self.project_window)
            return
        self._refresh_projects_table()
        self._load_dashboard_data()

    def _can_manage_tasks(self) -> bool:
        if not self.session_user:
            return False
        role = str(self.session_user.get("role", "executor"))
        return role in {"admin", "head", "teamlead", "curator"}

    def _open_tasks_window(self) -> None:
        if self.task_window and self.task_window.winfo_exists():
            self.task_window.lift()
            self.task_window.focus_force()
            self._refresh_tasks_table()
            return
        w = self._create_popup(self)
        w.title("Справочник: Задачи")
        w.geometry("1320x640")
        self.task_window = w
        w.protocol("WM_DELETE_WINDOW", self._close_tasks_window)

        top_bar = ttk.Frame(w, padding=(10, 10))
        top_bar.pack(fill="x")
        ttk.Label(top_bar, text="Показать:").pack(side=LEFT, padx=(0, 4))
        status_combo = ttk.Combobox(
            top_bar,
            textvariable=self.task_status_filter_var,
            values=["Активные", "Завершенные", "Все"],
            state="readonly",
            width=14,
        )
        status_combo.pack(side=LEFT)
        status_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_tasks_table())
        self._mk_button(top_bar, "Обновить", self._refresh_tasks_table).pack(side=LEFT, padx=6)
        self._mk_button(top_bar, "Закрыть", self._close_tasks_window).pack(side=RIGHT)

        table_frame = ttk.Frame(w, padding=(10, 0))
        table_frame.pack(fill=BOTH, expand=True)
        cols = (
            "id",
            "pocket_name",
            "project_name",
            "status",
            "description",
            "executor",
            "customer",
            "date_created",
            "date_start_work",
            "date_done",
            "code_link",
        )
        self.task_tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        headers = {
            "id": "ID",
            "pocket_name": "Карман",
            "project_name": "Проект",
            "status": "Статус",
            "description": "Описание",
            "executor": "Исполнитель",
            "customer": "Заказчик",
            "date_created": "Создана",
            "date_start_work": "Старт",
            "date_done": "Завершена",
            "code_link": "Код/ссылка",
        }
        for col in cols:
            self.task_tree.heading(col, text=headers.get(col, col))
            self.task_tree.column(col, width=120, anchor="w")
        self.task_tree.column("id", width=70, anchor="center")
        self.task_tree.column("status", width=120, anchor="center")
        self.task_tree.column("description", width=320)
        self.task_tree.pack(fill=BOTH, expand=True)
        self.task_tree.bind("<Double-1>", self._on_task_double_click)

        actions = ttk.Frame(w, padding=(10, 10))
        actions.pack(fill="x")
        self._mk_button(actions, "Создать", self._open_task_form_create).pack(side=LEFT, padx=2)
        self._mk_button(actions, "Изменить", self._open_task_form_edit).pack(side=LEFT, padx=2)
        self._mk_button(actions, "Старт", lambda: self._task_status_action("start")).pack(side=LEFT, padx=2)
        self._mk_button(actions, "Пауза", lambda: self._task_status_action("pause")).pack(side=LEFT, padx=2)
        self._mk_button(actions, "Возобновить", lambda: self._task_status_action("resume")).pack(side=LEFT, padx=2)
        self._mk_button(actions, "Завершить", lambda: self._task_status_action("complete")).pack(side=LEFT, padx=2)

        if not self._can_manage_tasks():
            for child in actions.winfo_children():
                if isinstance(child, ttk.Button):
                    child.state(["disabled"])

        self._refresh_tasks_table()

    def _close_tasks_window(self) -> None:
        if self.task_window and self.task_window.winfo_exists():
            self.task_window.destroy()
        self.task_window = None
        self.task_tree = None
        self.tasks_map = {}

    def _refresh_tasks_table(self) -> None:
        if not self.task_tree:
            return
        try:
            users = {int(u["id"]): u for u in self.api.list_users()}
            pockets = {int(p["id"]): p for p in self.api.list_pockets()}
            projects = {int(p["id"]): p for p in self.api.list_projects()}
            tasks = self.api.list_tasks()
        except ApiClientError as exc:
            messagebox.showerror("Ошибка API", f"Не удалось загрузить задачи.\n{exc}", parent=self.task_window)
            return
        mode = self.task_status_filter_var.get()
        if mode == "Активные":
            tasks = [t for t in tasks if str(t.get("status")) != "Завершена"]
        elif mode == "Завершенные":
            tasks = [t for t in tasks if str(t.get("status")) == "Завершена"]
        self.tasks_map = {int(t["id"]): t for t in tasks}

        self.task_tree.delete(*self.task_tree.get_children())
        rows_for_width: list[tuple[Any, ...]] = []
        for task in tasks:
            project = projects.get(int(task.get("project_id", 0)), {})
            pocket = pockets.get(int(project.get("pocket_id", 0)), {})
            executor = users.get(int(task.get("executor_user_id") or 0), {})
            values = (
                task.get("id", ""),
                pocket.get("name", ""),
                project.get("name", ""),
                task.get("status", ""),
                task.get("description", ""),
                executor.get("full_name", ""),
                task.get("customer", ""),
                task.get("date_created", ""),
                task.get("date_start_work", "") or "-",
                task.get("date_done", "") or "-",
                task.get("code_link", "") or "",
            )
            rows_for_width.append(values)
            self.task_tree.insert("", END, iid=str(task["id"]), values=values)
        self._autosize_tree_columns(
            self.task_tree,
            (
                "id",
                "pocket_name",
                "project_name",
                "status",
                "description",
                "executor",
                "customer",
                "date_created",
                "date_start_work",
                "date_done",
                "code_link",
            ),
            rows_for_width,
            min_width=90,
            max_width_overrides={"description": 440, "project_name": 220, "pocket_name": 220, "code_link": 220},
        )

    def _selected_task_id(self) -> int | None:
        if not self.task_tree:
            return None
        selected = self.task_tree.selection()
        if not selected:
            return None
        return int(selected[0])

    def _on_task_double_click(self, event: object) -> None:
        if not self.task_tree:
            return
        row_id = self.task_tree.identify_row(getattr(event, "y", 0))
        if row_id:
            self.task_tree.selection_set(row_id)
            self.task_tree.focus(row_id)
        self._open_task_form_edit()

    def _open_task_form_create(self) -> None:
        self._open_task_form(mode="create", task=None)

    def _open_task_form_edit(self) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            messagebox.showinfo("Задачи", "Выберите задачу.", parent=self.task_window)
            return
        task = self.tasks_map.get(task_id)
        if not task:
            messagebox.showerror("Задачи", "Задача не найдена.", parent=self.task_window)
            return
        self._open_task_form(mode="edit", task=task)

    def _open_task_form(self, *, mode: str, task: dict[str, Any] | None) -> None:
        if not self._can_manage_tasks():
            messagebox.showwarning("Недостаточно прав", "Доступно только ролям curator и выше.", parent=self.task_window)
            return
        try:
            raw_users = self.api.list_users()
            users = {int(u["id"]): u for u in raw_users if int(u.get("is_active", 1)) == 1}
            pockets = {int(p["id"]): p for p in self.api.list_pockets()}
            projects = self.api.list_projects()
            if task and task.get("executor_user_id") is not None:
                ex_uid = int(task["executor_user_id"])
                if ex_uid not in users:
                    found = next((u for u in raw_users if int(u["id"]) == ex_uid), None)
                    if found:
                        users[ex_uid] = found
        except ApiClientError as exc:
            messagebox.showerror("Ошибка API", f"Не удалось загрузить справочники.\n{exc}", parent=self.task_window)
            return

        pocket_items = [(int(p["id"]), str(p.get("name", ""))) for p in pockets.values()]
        pocket_items.sort(key=lambda x: x[1].lower())
        pocket_label_to_id = {f"{name} (id:{pid})": pid for pid, name in pocket_items}
        pocket_options = list(pocket_label_to_id.keys())
        projects_by_pocket: dict[int, list[tuple[int, str]]] = {}
        for p in projects:
            pid = int(p.get("pocket_id", 0))
            label = f"{p.get('name', '')} (id:{int(p['id'])})"
            projects_by_pocket.setdefault(pid, []).append((int(p["id"]), label))
        for values in projects_by_pocket.values():
            values.sort(key=lambda x: x[1].lower())

        user_items = [(int(u["id"]), str(u.get("full_name", ""))) for _, u in sorted(users.items(), key=lambda item: str(item[1].get("full_name", "")))]
        user_label_to_id = {f"{full_name} (id:{uid})": uid for uid, full_name in user_items}
        user_options = ["(Не назначен)"] + list(user_label_to_id.keys())
        customer_options = sorted({full_name for _, full_name in user_items if full_name})

        w = self._create_popup(self.task_window or self)
        w.title("Новая задача" if mode == "create" else f"Изменить задачу #{task.get('id') if task else ''}")
        w.geometry("740x540")
        frame = ttk.Frame(w, padding=(14, 14))
        frame.pack(fill=BOTH, expand=True)

        pocket_var = StringVar(value=(pocket_options[0] if pocket_options else ""))
        project_var = StringVar(value="")
        desc_var = StringVar(value=(task.get("description", "") if task else ""))
        customer_var = StringVar(value=(task.get("customer", "") if task else ""))
        code_link_var = StringVar(value=(task.get("code_link", "") if task and task.get("code_link") else ""))
        executor_var = StringVar(value="(Не назначен)")
        status_var = StringVar(value=(task.get("status", "Создана") if task else "Создана"))

        if task:
            pid = int(task.get("project_id", 0))
            project_obj = next((p for p in projects if int(p["id"]) == pid), None)
            if project_obj:
                pocket_id = int(project_obj.get("pocket_id", 0))
                pocket_name = pockets.get(pocket_id, {}).get("name", "")
                pocket_var.set(f"{pocket_name} (id:{pocket_id})")
                project_var.set(f"{project_obj.get('name', '')} (id:{pid})")
            ex_id = task.get("executor_user_id")
            if ex_id is not None:
                ex_name = users.get(int(ex_id), {}).get("full_name", "")
                executor_var.set(f"{ex_name} (id:{int(ex_id)})")

        basic = ttk.LabelFrame(frame, text="Основные данные", padding=(10, 10))
        basic.pack(fill="x")
        basic.columnconfigure(1, weight=1)
        ttk.Label(basic, text="Карман *").grid(row=0, column=0, sticky="w", pady=4, padx=(0, 8))
        pocket_combo = ttk.Combobox(basic, textvariable=pocket_var, values=pocket_options, state="readonly")
        pocket_combo.grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Label(basic, text="Проект *").grid(row=1, column=0, sticky="w", pady=4, padx=(0, 8))
        project_combo = ttk.Combobox(basic, textvariable=project_var, values=[], state="readonly")
        project_combo.grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Label(basic, text="Описание *").grid(row=2, column=0, sticky="w", pady=4, padx=(0, 8))
        ttk.Entry(basic, textvariable=desc_var).grid(row=2, column=1, sticky="ew", pady=4)
        ttk.Label(basic, text="Исполнитель").grid(row=3, column=0, sticky="w", pady=4, padx=(0, 8))
        ttk.Combobox(basic, textvariable=executor_var, values=user_options, state="readonly").grid(row=3, column=1, sticky="ew", pady=4)
        ttk.Label(basic, text="Заказчик *").grid(row=4, column=0, sticky="w", pady=4, padx=(0, 8))
        ttk.Combobox(basic, textvariable=customer_var, values=customer_options, state="normal").grid(
            row=4, column=1, sticky="ew", pady=4
        )
        ttk.Label(basic, text="Код/ссылка").grid(row=5, column=0, sticky="w", pady=4, padx=(0, 8))
        ttk.Entry(basic, textvariable=code_link_var).grid(row=5, column=1, sticky="ew", pady=4)
        if mode == "edit":
            ttk.Label(basic, text="Статус").grid(row=6, column=0, sticky="w", pady=4, padx=(0, 8))
            ttk.Combobox(
                basic,
                textvariable=status_var,
                values=["Создана", "В работе", "Приостановлена", "Завершена"],
                state="readonly",
            ).grid(row=6, column=1, sticky="ew", pady=4)

        def refresh_project_options(*_: object) -> None:
            pocket_label = pocket_var.get().strip()
            pocket_id = pocket_label_to_id.get(pocket_label)
            options = []
            if pocket_id is not None:
                options = [label for _, label in projects_by_pocket.get(pocket_id, [])]
            project_combo["values"] = options
            if project_var.get().strip() not in options:
                project_var.set("")

        pocket_combo.bind("<<ComboboxSelected>>", refresh_project_options)
        refresh_project_options()

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(16, 0))

        def save_form() -> None:
            pocket_id = pocket_label_to_id.get(pocket_var.get().strip())
            if pocket_id is None:
                messagebox.showerror("Валидация", "Выберите карман.", parent=w)
                return
            project_label = project_var.get().strip()
            project_id = None
            for pid, label in projects_by_pocket.get(pocket_id, []):
                if label == project_label:
                    project_id = pid
                    break
            if project_id is None:
                messagebox.showerror("Валидация", "Выберите проект.", parent=w)
                return
            description = desc_var.get().strip()
            customer = customer_var.get().strip()
            if not description:
                messagebox.showerror("Валидация", "Поле 'Описание' обязательно.", parent=w)
                return
            if not customer:
                messagebox.showerror("Валидация", "Поле 'Заказчик' обязательно.", parent=w)
                return
            executor_id: int | None = None
            ex_selected = executor_var.get().strip()
            if ex_selected and ex_selected != "(Не назначен)":
                executor_id = user_label_to_id.get(ex_selected)
                if executor_id is None:
                    messagebox.showerror("Валидация", "Некорректный исполнитель.", parent=w)
                    return
            payload: dict[str, Any] = {
                "project_id": project_id,
                "description": description,
                "customer": customer,
                "executor_user_id": executor_id,
                "code_link": code_link_var.get().strip() or None,
            }
            old_status = ""
            new_status = ""
            if mode == "edit" and task is not None:
                old_status = str(task.get("status", ""))
                new_status = status_var.get().strip()
                if new_status and new_status != old_status:
                    action_map = {
                        ("Создана", "В работе"): "start",
                        ("В работе", "Приостановлена"): "pause",
                        ("Приостановлена", "В работе"): "resume",
                        ("В работе", "Завершена"): "complete",
                    }
                    if (old_status, new_status) not in action_map:
                        messagebox.showerror(
                            "Статус",
                            f"Недопустимый переход статуса: {old_status} -> {new_status}",
                            parent=w,
                        )
                        return
            try:
                if mode == "create":
                    self.api.create_task(payload)
                else:
                    assert task is not None
                    upd = {
                        "project_id": project_id,
                        "description": payload["description"],
                        "customer": payload["customer"],
                        "executor_user_id": payload["executor_user_id"],
                        "code_link": payload["code_link"],
                    }
                    self.api.update_task(int(task["id"]), upd)
                    if new_status and new_status != old_status:
                        action_map = {
                            ("Создана", "В работе"): "start",
                            ("В работе", "Приостановлена"): "pause",
                            ("Приостановлена", "В работе"): "resume",
                            ("В работе", "Завершена"): "complete",
                        }
                        action = action_map[(old_status, new_status)]
                        self.api.task_action(int(task["id"]), action)
            except ApiClientError as exc:
                messagebox.showerror("Ошибка API", f"Сохранить задачу не удалось.\n{exc}", parent=w)
                return
            w.destroy()
            self._refresh_tasks_table()
            self._load_dashboard_data()

        self._mk_button(buttons, "Сохранить", save_form).pack(side=LEFT)
        self._mk_button(buttons, "Отмена", w.destroy).pack(side=LEFT, padx=6)

    def _task_status_action(self, action: str) -> None:
        if not self._can_manage_tasks():
            messagebox.showwarning("Недостаточно прав", "Доступно только ролям curator и выше.", parent=self.task_window)
            return
        task_id = self._selected_task_id()
        if task_id is None:
            messagebox.showinfo("Задачи", "Выберите задачу.", parent=self.task_window)
            return
        try:
            self.api.task_action(task_id, action)
        except ApiClientError as exc:
            messagebox.showerror("Ошибка API", f"Изменение статуса не удалось.\n{exc}", parent=self.task_window)
            return
        self._refresh_tasks_table()
        self._load_dashboard_data()

    def _reset_kanban_filters(self) -> None:
        self.global_filter_context.rows = [FilterRowState(logic="AND", field="status", op="!=", value="Завершена")]
        self.global_filter_context.preset_name = DEFAULT_PRESET_NAME
        self.global_filter_context.dashboard_visible = False
        self.global_filter_context.kanban_visible = False
        self.global_filter_context.timeline_visible = False
        self.global_filter_context.analytics_visible = False
        self.selected_project_id = None
        if hasattr(self, "top_tree"):
            self._suppress_top_select_event = True
            try:
                self.top_tree.selection_remove(*self.top_tree.selection())
            finally:
                self._suppress_top_select_event = False
        self._apply_global_filter_context_to_zone("dashboard")
        self._apply_global_filter_context_to_zone("kanban")
        self._apply_global_filter_context_to_zone("timeline")
        self._apply_global_filter_context_to_zone("analytics")
        if hasattr(self, "preset_var"):
            self.preset_var.set(DEFAULT_PRESET_NAME)
        if hasattr(self, "kanban_preset_var"):
            self.kanban_preset_var.set(DEFAULT_PRESET_NAME)
        if hasattr(self, "analytics_preset_var"):
            self.analytics_preset_var.set(DEFAULT_PRESET_NAME)
        self._refresh_global_filter_indicators()
        self._apply_filters()
        self._refresh_kanban_board()
        self._refresh_analytics()

    def _apply_kanban_filters(self) -> None:
        self._sync_global_filter_context_from_rows(
            self.kanban_filter_rows,
            zone="kanban",
            preset_name=self.kanban_preset_var.get() if hasattr(self, "kanban_preset_var") else DEFAULT_PRESET_NAME,
            visible=self.kanban_filter_visible,
        )
        self._apply_global_filter_context_to_zone("dashboard")
        self._apply_global_filter_context_to_zone("timeline")
        self._apply_global_filter_context_to_zone("analytics")
        if hasattr(self, "preset_var"):
            preset_name = self.global_filter_context.preset_name
            self.preset_var.set(preset_name if preset_name in self.presets else DEFAULT_PRESET_NAME)
        if "timeline_preset_var" in self.__dict__:
            preset_name = self.global_filter_context.preset_name
            self.timeline_preset_var.set(preset_name if preset_name in self.presets else DEFAULT_PRESET_NAME)
        if "analytics_preset_var" in self.__dict__:
            preset_name = self.global_filter_context.preset_name
            self.analytics_preset_var.set(preset_name if preset_name in self.presets else DEFAULT_PRESET_NAME)
        self._refresh_dashboard_top_table_from_filter_context()
        self._refresh_dashboard_bottom_table_from_selection_and_filter()
        self._refresh_kanban_board()
        self._refresh_timeline()
        self._refresh_analytics()

    def _refresh_kanban_board(self) -> None:
        if not hasattr(self, "kanban_columns"):
            return
        self._ensure_kanban_icons_ready()
        rows = self._build_filtered_task_rows()
        grouped: dict[str, list[dict[str, Any]]] = {
            "queue": [],
            "created": [],
            "in_progress": [],
            "paused": [],
            "done": [],
        }
        for row in rows:
            status_name = str(row.get("status", ""))
            has_executor = row.get("executor_user_id") is not None
            if status_name == "Создана" and not has_executor:
                grouped["queue"].append(row)
                continue
            if status_name == "Создана" and has_executor:
                grouped["created"].append(row)
            elif status_name == "В работе":
                grouped["in_progress"].append(row)
            elif status_name == "Приостановлена":
                grouped["paused"].append(row)
            elif status_name == "Завершена":
                grouped["done"].append(row)
            else:
                grouped["created"].append(row)

        for key, holder in self.kanban_columns.items():
            for child in holder.winfo_children():
                child.destroy()
            if not grouped[key]:
                ttk.Label(holder, text="\u041d\u0435\u0442 \u0437\u0430\u0434\u0430\u0447", style="Surface.TLabel").pack(anchor="center", pady=12)
            holder.update_idletasks()
            canvas = self.kanban_column_canvases.get(key)
            if canvas is not None:
                canvas.configure(scrollregion=canvas.bbox("all"))
                canvas.yview_moveto(0)
            if not grouped[key]:
                continue
            for task in grouped[key]:
                self._render_kanban_card(holder, task, queue=(key == "queue"))
            holder.update_idletasks()
            if canvas is not None:
                canvas.configure(scrollregion=canvas.bbox("all"))
        self._refresh_kanban_filter_indicator()

    def _render_kanban_card(self, parent: ttk.Frame, task: dict[str, Any], *, queue: bool) -> None:
        card = ttk.Frame(parent, padding=(8, 8), style="Surface.TFrame", width=248, height=164)
        card.pack(fill="x", pady=4)
        card.pack_propagate(False)

        content = ttk.Frame(card, style="Surface.TFrame", height=108)
        content.pack(fill="x", expand=True)
        content.pack_propagate(False)

        description = str(task.get("description", "")).strip()
        if len(description) > 64:
            description = f"{description[:64].rstrip()}..."
        lines = [
            f"#{task.get('id')} {description}",
            f"{task.get('pocket_name', '')} / {task.get('project_name', '')}",
            f"Исполнитель: {task.get('executor_full_name') or '-'}",
            f"Статус: {task.get('status')}",
        ]
        for line in lines:
            lbl = ttk.Label(content, text=line, style="Surface.TLabel", wraplength=228)
            lbl.pack(anchor="w")
            lbl.bind("<Double-1>", lambda _e, t=task: self._open_task_form(mode="edit", task=t))
        card.bind("<Double-1>", lambda _e, t=task: self._open_task_form(mode="edit", task=t))

        actions = ttk.Frame(card, style="Surface.TFrame")
        actions.pack(side=BOTTOM, fill="x", pady=(6, 0))
        task_id = int(task["id"])
        if queue and self.session_user is not None:
            role = str(self.session_user.get("role", "executor"))
            if role in {"curator", "teamlead", "head", "admin"}:
                self._add_kanban_action_button(
                    actions,
                    "assign",
                    "Назначить исполнителя",
                    lambda tid=task_id: self._open_kanban_assign_popup(tid),
                    padx=4,
                )
        if self._can_manage_tasks():
            status_name = str(task.get("status", ""))
            if status_name == "Создана" and task.get("executor_user_id") is not None:
                self._add_kanban_action_button(actions, "start", "Старт", lambda tid=task_id: self._kanban_task_action(tid, "start"))
            elif status_name == "В работе":
                self._add_kanban_action_button(actions, "pause", "Пауза", lambda tid=task_id: self._kanban_task_action(tid, "pause"))
                self._add_kanban_action_button(
                    actions,
                    "complete",
                    "Завершить",
                    lambda tid=task_id: self._kanban_task_action(tid, "complete"),
                    padx=4,
                )
            elif status_name == "Приостановлена":
                self._add_kanban_action_button(actions, "resume", "Возобновить", lambda tid=task_id: self._kanban_task_action(tid, "resume"))
                self._add_kanban_action_button(
                    actions,
                    "complete",
                    "Завершить",
                    lambda tid=task_id: self._kanban_task_action(tid, "complete"),
                    padx=4,
                )

    def _add_kanban_action_button(
        self,
        parent: ttk.Frame,
        action_key: str,
        tooltip: str,
        command: Any,
        *,
        padx: int = 0,
    ) -> ttk.Button:
        icon_image = self.icon_images.get(action_key)
        if icon_image is None:
            # Try one more time before rendering fallback text.
            self._ensure_kanban_icons_ready()
            icon_image = self.icon_images.get(action_key)
        if icon_image is None:
            fallback_text = {
                "assign": "A",
                "start": "S",
                "pause": "P",
                "resume": "R",
                "complete": "D",
            }.get(action_key, "?")
            button = self._mk_button(parent, fallback_text, command, width=3, style="KanbanAction.TButton")
        else:
            button = self._mk_button(parent, "", command, width=4, style="KanbanAction.TButton")
            button.configure(image=icon_image, compound="center")
            button.image = icon_image
        self._attach_tooltip(button, tooltip)
        button.pack(side=LEFT, padx=padx)
        return button

    def _kanban_task_action(self, task_id: int, action: str) -> None:
        try:
            self.api.task_action(task_id, action)
        except ApiClientError as exc:
            messagebox.showerror("Ошибка API", f"Изменение статуса не удалось.\n{exc}", parent=self)
            return
        self._load_dashboard_data()
        self._refresh_kanban_board()

    def _kanban_claim_task(self, task_id: int) -> None:
        try:
            self.api.claim_task(task_id)
        except ApiClientError as exc:
            messagebox.showerror("Ошибка API", f"Принять задачу не удалось.\n{exc}", parent=self)
            return
        self._load_dashboard_data()
        self._refresh_kanban_board()

    def _open_kanban_assign_popup(self, task_id: int) -> None:
        if not self._can_manage_tasks():
            messagebox.showwarning("Недостаточно прав", "Назначение доступно для роли куратор и выше.", parent=self)
            return
        try:
            users = [u for u in self.api.list_users() if int(u.get("is_active", 1)) == 1]
        except ApiClientError as exc:
            messagebox.showerror("Ошибка API", f"Не удалось загрузить пользователей.\n{exc}", parent=self)
            return
        if not users:
            messagebox.showwarning("Назначение", "Активные пользователи не найдены.", parent=self)
            return

        labels = [f"{u.get('full_name', '')} (id:{u['id']})" for u in users]
        label_to_id = {label: int(u["id"]) for label, u in zip(labels, users)}
        w = self._create_popup(self)
        w.title(f"Назначить исполнителя для задачи #{task_id}")
        w.geometry("460x140")
        body = ttk.Frame(w, padding=(12, 12))
        body.pack(fill=BOTH, expand=True)
        ttk.Label(body, text="Исполнитель *").pack(anchor="w")
        selected_var = StringVar(value=labels[0])
        ttk.Combobox(body, textvariable=selected_var, values=labels, state="readonly").pack(fill="x", pady=(4, 8))
        buttons = ttk.Frame(body)
        buttons.pack(fill="x")

        def do_assign() -> None:
            selected = selected_var.get().strip()
            executor_id = label_to_id.get(selected)
            if executor_id is None:
                messagebox.showerror("Валидация", "Выберите исполнителя из списка.", parent=w)
                return
            try:
                self.api.assign_task(task_id, executor_id)
            except ApiClientError as exc:
                messagebox.showerror("Ошибка API", f"Назначение не удалось.\n{exc}", parent=w)
                return
            w.destroy()
            self._load_dashboard_data()
            self._refresh_kanban_board()

        self._mk_button(buttons, "Назначить", do_assign).pack(side=LEFT)
        self._mk_button(buttons, "Отмена", w.destroy).pack(side=LEFT, padx=6)

    def _is_admin(self) -> bool:
        if not self.session_user:
            return False
        return str(self.session_user.get("role", "")) == "admin"

    def _open_users_window(self) -> None:
        if self.users_window and self.users_window.winfo_exists():
            self.users_window.lift()
            self.users_window.focus_force()
            self._refresh_users_table()
            return
        w = self._create_popup(self)
        w.title("Справочник: Пользователи")
        w.geometry("980x560")
        self.users_window = w
        w.protocol("WM_DELETE_WINDOW", self._close_users_window)

        top = ttk.Frame(w, padding=(10, 10))
        top.pack(fill="x")
        self._mk_button(top, "Обновить", self._refresh_users_table).pack(side=LEFT)
        self._mk_button(top, "Закрыть", self._close_users_window).pack(side=RIGHT)

        table = ttk.Frame(w, padding=(10, 0))
        table.pack(fill=BOTH, expand=True)
        cols = ("id", "login", "full_name", "role", "status_name")
        self.users_tree = ttk.Treeview(table, columns=cols, show="headings")
        headers = {
            "id": "ID",
            "login": "Логин",
            "full_name": "ФИО",
            "role": "Роль",
            "status_name": "Статус",
        }
        for col in cols:
            self.users_tree.heading(col, text=headers[col])
            self.users_tree.column(col, width=120, anchor="w")
        self.users_tree.column("id", width=70, anchor="center")
        self.users_tree.pack(fill=BOTH, expand=True)
        self.users_tree.bind("<Double-1>", lambda _e: self._open_user_form_edit())

        actions = ttk.Frame(w, padding=(10, 10))
        actions.pack(fill="x")
        self._mk_button(actions, "Создать", self._open_user_form_create).pack(side=LEFT, padx=2)
        self._mk_button(actions, "Изменить", self._open_user_form_edit).pack(side=LEFT, padx=2)
        self._mk_button(actions, "Деактивировать", self._deactivate_selected_user).pack(side=LEFT, padx=2)
        if not self._is_admin():
            for child in actions.winfo_children():
                if isinstance(child, ttk.Button):
                    child.state(["disabled"])
        self._refresh_users_table()

    def _close_users_window(self) -> None:
        if self.users_window and self.users_window.winfo_exists():
            self.users_window.destroy()
        self.users_window = None
        self.users_tree = None

    def _refresh_users_table(self) -> None:
        if not self.users_tree:
            return
        try:
            rows = self.api.list_users()
        except ApiClientError as exc:
            messagebox.showerror("Ошибка API", f"Не удалось загрузить пользователей.\n{exc}", parent=self.users_window)
            return
        self.users_tree.delete(*self.users_tree.get_children())
        autosize_rows: list[tuple[Any, ...]] = []
        for row in rows:
            values = (
                row.get("id", ""),
                row.get("login", ""),
                row.get("full_name", ""),
                row.get("role", ""),
                row.get("status_name", ""),
            )
            autosize_rows.append(values)
            self.users_tree.insert("", END, iid=str(row.get("id")), values=values)
        self._autosize_tree_columns(
            self.users_tree,
            ("id", "login", "full_name", "role", "status_name"),
            autosize_rows,
            min_width=90,
            max_width_overrides={"full_name": 260},
        )

    def _selected_user_id(self) -> int | None:
        if not self.users_tree:
            return None
        selected = self.users_tree.selection()
        if not selected:
            return None
        return int(selected[0])

    def _open_user_form_create(self) -> None:
        self._open_user_form(mode="create", user=None)

    def _open_user_form_edit(self) -> None:
        user_id = self._selected_user_id()
        if user_id is None:
            messagebox.showinfo("Пользователи", "Выберите пользователя.", parent=self.users_window)
            return
        try:
            user = next((u for u in self.api.list_users() if int(u["id"]) == user_id), None)
        except ApiClientError as exc:
            messagebox.showerror("Ошибка API", f"Не удалось загрузить пользователя.\n{exc}", parent=self.users_window)
            return
        if not user:
            messagebox.showerror("Пользователи", "Пользователь не найден.", parent=self.users_window)
            return
        self._open_user_form(mode="edit", user=user)

    def _open_user_form(self, *, mode: str, user: dict[str, Any] | None) -> None:
        if not self._is_admin():
            messagebox.showwarning("Недостаточно прав", "Только admin.", parent=self.users_window)
            return
        try:
            statuses = self.api.list_statuses(entity_type="user", is_active=True)
        except ApiClientError as exc:
            messagebox.showerror("Ошибка API", f"Не удалось загрузить статусы.\n{exc}", parent=self.users_window)
            return
        status_options = [f"{s.get('name', '')} (id:{s['id']})" for s in statuses]
        status_label_to_id = {label: int(s["id"]) for label, s in zip(status_options, statuses)}

        w = self._create_popup(self.users_window or self)
        w.title("Новый пользователь" if mode == "create" else f"Изменить пользователя #{user.get('id') if user else ''}")
        w.geometry("560x360")
        frame = ttk.Frame(w, padding=(14, 14))
        frame.pack(fill=BOTH, expand=True)
        login_var = StringVar(value=(user.get("login", "") if user else ""))
        full_name_var = StringVar(value=(user.get("full_name", "") if user else ""))
        role_var = StringVar(value=(user.get("role", "executor") if user else "executor"))
        status_var = StringVar(value=(status_options[0] if status_options else ""))
        if user and user.get("status_id"):
            sid = int(user["status_id"])
            for label in status_options:
                if f"id:{sid})" in label:
                    status_var.set(label)
                    break

        lf = ttk.LabelFrame(frame, text="Данные пользователя", padding=(10, 10))
        lf.pack(fill="x")
        lf.columnconfigure(1, weight=1)
        ttk.Label(lf, text="Логин *").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        login_entry = ttk.Entry(lf, textvariable=login_var)
        login_entry.grid(row=0, column=1, sticky="ew", pady=4)
        if mode == "edit":
            login_entry.state(["disabled"])
        ttk.Label(lf, text="ФИО *").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(lf, textvariable=full_name_var).grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Label(lf, text="Роль *").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Combobox(lf, textvariable=role_var, values=["admin", "head", "teamlead", "curator", "executor"], state="readonly").grid(row=2, column=1, sticky="ew", pady=4)
        ttk.Label(lf, text="Статус").grid(row=3, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Combobox(lf, textvariable=status_var, values=status_options, state="readonly").grid(row=3, column=1, sticky="ew", pady=4)

        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=(16, 0))

        def save_user() -> None:
            login = login_var.get().strip()
            full_name = full_name_var.get().strip()
            if mode == "create" and not login:
                messagebox.showerror("Валидация", "Логин обязателен.", parent=w)
                return
            if not full_name:
                messagebox.showerror("Валидация", "ФИО обязательно.", parent=w)
                return
            sid = status_label_to_id.get(status_var.get().strip()) if status_var.get().strip() else None
            payload = {
                "full_name": full_name,
                "role": role_var.get().strip(),
                "status_id": sid,
            }
            try:
                if mode == "create":
                    create_payload = dict(payload)
                    create_payload["login"] = login
                    self.api.create_user(create_payload)
                else:
                    assert user is not None
                    self.api.update_user(int(user["id"]), payload)
            except ApiClientError as exc:
                messagebox.showerror("Ошибка API", f"Сохранить пользователя не удалось.\n{exc}", parent=w)
                return
            w.destroy()
            self._refresh_users_table()
            self._load_dashboard_data()

        self._mk_button(actions, "Сохранить", save_user).pack(side=LEFT)
        self._mk_button(actions, "Отмена", w.destroy).pack(side=LEFT, padx=6)

    def _deactivate_selected_user(self) -> None:
        if not self._is_admin():
            messagebox.showwarning("Недостаточно прав", "Только admin.", parent=self.users_window)
            return
        user_id = self._selected_user_id()
        if user_id is None:
            messagebox.showinfo("Пользователи", "Выберите пользователя.", parent=self.users_window)
            return
        if self.session_user and int(self.session_user.get("id", 0)) == user_id:
            messagebox.showwarning("Ограничение", "Нельзя деактивировать текущего пользователя сессии.", parent=self.users_window)
            return
        if not messagebox.askyesno("Подтверждение", "Деактивировать пользователя?", parent=self.users_window):
            return
        try:
            self.api.deactivate_user(user_id)
        except ApiClientError as exc:
            messagebox.showerror("Ошибка API", f"Деактивация не удалась.\n{exc}", parent=self.users_window)
            return
        self._refresh_users_table()
        self._load_dashboard_data()

    def _open_statuses_window(self) -> None:
        if self.statuses_window and self.statuses_window.winfo_exists():
            self.statuses_window.lift()
            self.statuses_window.focus_force()
            self._refresh_statuses_table()
            return
        w = self._create_popup(self)
        w.title("Справочник: Статусы")
        w.geometry("980x560")
        self.statuses_window = w
        w.protocol("WM_DELETE_WINDOW", self._close_statuses_window)

        top = ttk.Frame(w, padding=(10, 10))
        top.pack(fill="x")
        ttk.Label(top, text="Сущность:").pack(side=LEFT)
        ttk.Combobox(
            top,
            textvariable=self.status_entity_filter_var,
            values=["user", "pocket", "project", "task"],
            state="readonly",
            width=12,
        ).pack(side=LEFT, padx=6)
        self._mk_button(top, "Обновить", self._refresh_statuses_table).pack(side=LEFT)
        self._mk_button(top, "Закрыть", self._close_statuses_window).pack(side=RIGHT)

        table = ttk.Frame(w, padding=(10, 0))
        table.pack(fill=BOTH, expand=True)
        cols = ("id", "entity_type", "code", "name", "is_active", "sort_order", "is_system")
        self.statuses_tree = ttk.Treeview(table, columns=cols, show="headings")
        headers = {
            "id": "ID",
            "entity_type": "Сущность",
            "code": "Код",
            "name": "Наименование",
            "is_active": "Активен",
            "sort_order": "Порядок",
            "is_system": "Системный",
        }
        for col in cols:
            self.statuses_tree.heading(col, text=headers[col])
            self.statuses_tree.column(col, width=120, anchor="w")
        self.statuses_tree.column("id", width=70, anchor="center")
        self.statuses_tree.pack(fill=BOTH, expand=True)
        self.statuses_tree.bind("<Double-1>", lambda _e: self._open_status_form_edit())

        actions = ttk.Frame(w, padding=(10, 10))
        actions.pack(fill="x")
        self._mk_button(actions, "Создать", self._open_status_form_create).pack(side=LEFT, padx=2)
        self._mk_button(actions, "Изменить", self._open_status_form_edit).pack(side=LEFT, padx=2)
        self._mk_button(actions, "Деактивировать", self._deactivate_selected_status).pack(side=LEFT, padx=2)
        self._mk_button(actions, "Удалить", self._delete_selected_status).pack(side=LEFT, padx=2)
        if not self._is_admin():
            for child in actions.winfo_children():
                if isinstance(child, ttk.Button):
                    child.state(["disabled"])

        self._refresh_statuses_table()

    def _close_statuses_window(self) -> None:
        if self.statuses_window and self.statuses_window.winfo_exists():
            self.statuses_window.destroy()
        self.statuses_window = None
        self.statuses_tree = None

    def _refresh_statuses_table(self) -> None:
        if not self.statuses_tree:
            return
        try:
            rows = self.api.list_statuses(entity_type=self.status_entity_filter_var.get().strip() or None, is_active=None)
        except ApiClientError as exc:
            messagebox.showerror("Ошибка API", f"Не удалось загрузить статусы.\n{exc}", parent=self.statuses_window)
            return
        self.statuses_tree.delete(*self.statuses_tree.get_children())
        autosize_rows: list[tuple[Any, ...]] = []
        for row in rows:
            values = (
                row.get("id", ""),
                row.get("entity_type", ""),
                row.get("code", ""),
                row.get("name", ""),
                "Да" if int(row.get("is_active", 0)) == 1 else "Нет",
                row.get("sort_order", ""),
                "Да" if int(row.get("is_system", 0)) == 1 else "Нет",
            )
            autosize_rows.append(values)
            self.statuses_tree.insert("", END, iid=str(row.get("id")), values=values)
        self._autosize_tree_columns(
            self.statuses_tree,
            ("id", "entity_type", "code", "name", "is_active", "sort_order", "is_system"),
            autosize_rows,
            min_width=90,
            max_width_overrides={"name": 240},
        )

    def _selected_status_id(self) -> int | None:
        if not self.statuses_tree:
            return None
        selected = self.statuses_tree.selection()
        if not selected:
            return None
        return int(selected[0])

    def _open_status_form_create(self) -> None:
        self._open_status_form(mode="create", item=None)

    def _open_status_form_edit(self) -> None:
        sid = self._selected_status_id()
        if sid is None:
            messagebox.showinfo("Статусы", "Выберите статус.", parent=self.statuses_window)
            return
        try:
            item = next((s for s in self.api.list_statuses(is_active=None) if int(s["id"]) == sid), None)
        except ApiClientError as exc:
            messagebox.showerror("Ошибка API", f"Не удалось загрузить статус.\n{exc}", parent=self.statuses_window)
            return
        if not item:
            messagebox.showerror("Статусы", "Статус не найден.", parent=self.statuses_window)
            return
        self._open_status_form(mode="edit", item=item)

    def _open_status_form(self, *, mode: str, item: dict[str, Any] | None) -> None:
        if not self._is_admin():
            messagebox.showwarning("Недостаточно прав", "Только admin.", parent=self.statuses_window)
            return
        w = self._create_popup(self.statuses_window or self)
        w.title("Новый статус" if mode == "create" else f"Изменить статус #{item.get('id') if item else ''}")
        w.geometry("560x360")
        frame = ttk.Frame(w, padding=(14, 14))
        frame.pack(fill=BOTH, expand=True)
        entity_var = StringVar(value=(item.get("entity_type", self.status_entity_filter_var.get()) if item else self.status_entity_filter_var.get()))
        code_var = StringVar(value=(item.get("code", "") if item else ""))
        name_var = StringVar(value=(item.get("name", "") if item else ""))
        active_var = StringVar(value=("Да" if (not item or int(item.get("is_active", 0)) == 1) else "Нет"))
        order_var = StringVar(value=(str(item.get("sort_order", 100)) if item else "100"))

        lf = ttk.LabelFrame(frame, text="Параметры статуса", padding=(10, 10))
        lf.pack(fill="x")
        lf.columnconfigure(1, weight=1)
        ttk.Label(lf, text="Сущность *").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        entity_combo = ttk.Combobox(lf, textvariable=entity_var, values=["user", "pocket", "project", "task"], state="readonly")
        entity_combo.grid(row=0, column=1, sticky="ew", pady=4)
        if mode == "edit":
            entity_combo.state(["disabled"])
        ttk.Label(lf, text="Код *").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(lf, textvariable=code_var).grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Label(lf, text="Наименование *").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(lf, textvariable=name_var).grid(row=2, column=1, sticky="ew", pady=4)
        ttk.Label(lf, text="Порядок").grid(row=3, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(lf, textvariable=order_var).grid(row=3, column=1, sticky="ew", pady=4)
        ttk.Label(lf, text="Активен").grid(row=4, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Combobox(lf, textvariable=active_var, values=["Да", "Нет"], state="readonly").grid(row=4, column=1, sticky="ew", pady=4)

        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=(16, 0))

        def save_status() -> None:
            code = code_var.get().strip()
            name = name_var.get().strip()
            if not code or not name:
                messagebox.showerror("Валидация", "Код и наименование обязательны.", parent=w)
                return
            try:
                sort_order = int(order_var.get().strip() or "100")
            except ValueError:
                messagebox.showerror("Валидация", "Порядок должен быть числом.", parent=w)
                return
            payload = {
                "entity_type": entity_var.get().strip(),
                "code": code,
                "name": name,
                "is_active": active_var.get() == "Да",
                "sort_order": sort_order,
            }
            try:
                if mode == "create":
                    self.api.create_status(payload)
                else:
                    assert item is not None
                    self.api.update_status(int(item["id"]), payload)
            except ApiClientError as exc:
                messagebox.showerror("Ошибка API", f"Сохранить статус не удалось.\n{exc}", parent=w)
                return
            w.destroy()
            self._refresh_statuses_table()
            self._load_dashboard_data()

        self._mk_button(actions, "Сохранить", save_status).pack(side=LEFT)
        self._mk_button(actions, "Отмена", w.destroy).pack(side=LEFT, padx=6)

    def _deactivate_selected_status(self) -> None:
        sid = self._selected_status_id()
        if sid is None:
            messagebox.showinfo("Статусы", "Выберите статус.", parent=self.statuses_window)
            return
        try:
            self.api.update_status(sid, {"is_active": False})
        except ApiClientError as exc:
            messagebox.showerror("Ошибка API", f"Не удалось деактивировать статус.\n{exc}", parent=self.statuses_window)
            return
        self._refresh_statuses_table()

    def _delete_selected_status(self) -> None:
        sid = self._selected_status_id()
        if sid is None:
            messagebox.showinfo("Статусы", "Выберите статус.", parent=self.statuses_window)
            return
        if not messagebox.askyesno("Подтверждение", "Удалить выбранный статус?", parent=self.statuses_window):
            return
        try:
            self.api.delete_status(sid)
        except ApiClientError as exc:
            messagebox.showerror("Ошибка API", f"Удалить статус не удалось.\n{exc}", parent=self.statuses_window)
            return
        self._refresh_statuses_table()

    def _build_project_view_rows(self, projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for project in projects:
            pocket = self.pockets_by_id.get(int(project["pocket_id"]), {})
            owner = self.users_by_id.get(int(pocket.get("owner_user_id", 0)), {}).get("full_name", "")
            owner_it = self.users_by_id.get(int(project["curator_it_user_id"]), {}).get("full_name", "")
            rows.append(
                {
                    "pocket_id": pocket.get("id", ""),
                    "pocket_name": pocket.get("name", ""),
                    "project_id": project["id"],
                    "project_name": project["name"],
                    "project_code": project.get("project_code", "") or "",
                    "date_start": project.get("date_start") or "",
                    "date_end": project.get("date_end") or "",
                    "status": project.get("status") or "",
                    "owner": owner,
                    "owner_it": owner_it,
                }
            )
        return rows

    def _apply_project_table_filters(
        self,
        rows: list[dict[str, Any]],
        conditions: list[FilterRowState],
    ) -> list[dict[str, Any]]:
        project_conditions = [c for c in conditions if c.field in PROJECT_FILTER_FIELDS]
        if not project_conditions:
            return rows
        result = list(rows)
        for idx, cond in enumerate(project_conditions):
            logic = cond.logic if idx > 0 else "AND"
            source_rows = result if logic == "AND" else rows
            filtered = [r for r in source_rows if self._match_condition(r.get(cond.field), cond.op, cond.value)]
            if idx == 0 or logic == "AND":
                result = filtered
            else:
                ids = {int(r["project_id"]) for r in result}
                for item in filtered:
                    if int(item["project_id"]) not in ids:
                        result.append(item)
        return result

    def _fill_top_table(self, project_rows: list[dict[str, Any]]) -> None:
        self.top_tree.delete(*self.top_tree.get_children())
        rows_for_width: list[tuple[Any, ...]] = []
        for row in project_rows:
            values = (
                row.get("pocket_id", ""),
                row.get("pocket_name", ""),
                row.get("project_id", ""),
                row.get("project_name", ""),
                row.get("project_code", ""),
                row.get("date_start", ""),
                row.get("date_end", ""),
                row.get("status", ""),
                row.get("owner", ""),
                row.get("owner_it", ""),
            )
            rows_for_width.append(values)
            self.top_tree.insert("", END, iid=str(row.get("project_id")), values=values)
        self._autosize_tree_columns(
            self.top_tree,
            (
                "pocket_id",
                "pocket_name",
                "project_id",
                "project_name",
                "project_code",
                "date_start",
                "date_end",
                "status",
                "owner",
                "owner_it",
            ),
            rows_for_width,
            min_width=90,
            max_width_overrides={"project_name": 320, "owner": 220, "owner_it": 220},
        )
        self._update_top_tree_height(len(rows_for_width))

    def _update_top_tree_height(self, row_count: int) -> None:
        # Top table height follows data volume; bottom table takes remaining space.
        visible_rows = max(3, min(18, row_count if row_count > 0 else 3))
        self.top_tree.configure(height=visible_rows)

    def _reconcile_selected_project(self, project_rows: list[dict[str, Any]]) -> None:
        available_ids = {int(r["project_id"]) for r in project_rows}
        if self.selected_project_id is not None and self.selected_project_id not in available_ids:
            self.selected_project_id = None
            if "top_tree" in self.__dict__:
                self.top_tree.selection_remove(*self.top_tree.selection())

    def _refresh_dashboard_top_table_from_filter_context(self) -> None:
        filtered_tasks = self._build_filtered_task_rows()
        project_rows = self._build_top_rows_from_filtered_tasks(filtered_tasks)
        project_rows = self._augment_top_rows_with_empty_projects(project_rows)
        self._fill_top_table(project_rows)
        self._reconcile_selected_project(project_rows)
        if self.selected_project_id is not None and self.top_tree.exists(str(self.selected_project_id)):
            self._suppress_top_select_event = True
            try:
                self.top_tree.selection_set(str(self.selected_project_id))
                self.top_tree.focus(str(self.selected_project_id))
            finally:
                self._suppress_top_select_event = False

    def _refresh_dashboard_bottom_table_from_selection_and_filter(self) -> None:
        rows = self._build_filtered_task_rows()

        self.bottom_tree.delete(*self.bottom_tree.get_children())
        rows_for_width: list[tuple[Any, ...]] = []
        for row in rows:
            values = (
                row.get("id", ""),
                row.get("description", ""),
                row.get("status", ""),
                row.get("date_created", ""),
                row.get("date_start_work", ""),
                row.get("date_done", ""),
                row.get("executor_full_name", ""),
                row.get("customer", ""),
                row.get("code_link", ""),
            )
            rows_for_width.append(values)
            self.bottom_tree.insert("", END, iid=str(row.get("id")), values=values)
        self._autosize_tree_columns(
            self.bottom_tree,
            (
                "id",
                "description",
                "status",
                "date_created",
                "date_start_work",
                "date_done",
                "executor_full_name",
                "customer",
                "code_link",
            ),
            rows_for_width,
            min_width=90,
            max_width_overrides={"description": 520, "executor_full_name": 220, "customer": 180, "code_link": 220},
        )

    def _on_top_select(self, _: object) -> None:
        if self._in_filter_refresh or self._suppress_top_select_event:
            return
        selected = self.top_tree.selection()
        self.selected_project_id = int(selected[0]) if selected else None
        self._refresh_dashboard_bottom_table_from_selection_and_filter()
        self._refresh_kanban_board()
        self._refresh_global_filter_indicators()

    def _on_top_double_click(self, event: object) -> None:
        region = self.top_tree.identify_region(getattr(event, "x"), getattr(event, "y"))
        if region != "cell":
            return
        selected = self.top_tree.selection()
        if not selected:
            return
        project = self.projects_by_id.get(int(selected[0]))
        if project:
            self._open_project_form(mode="edit", project=project)

    def _on_bottom_double_click(self, event: object) -> None:
        row_id = self.bottom_tree.identify_row(getattr(event, "y", 0))
        if not row_id:
            return
        self.bottom_tree.selection_set(row_id)
        self.bottom_tree.focus(row_id)
        task_id = int(row_id)
        task = next((t for t in self.tasks_all if int(t.get("id", 0)) == task_id), None)
        if not task:
            messagebox.showerror("Задачи", "Задача не найдена.")
            return
        self._open_task_form(mode="edit", task=task)

    def _open_project_popup(self, project: dict[str, Any]) -> None:
        w = self._create_popup(self)
        w.title(f"Проект #{project['id']}")
        w.geometry("520x220")
        text = (
            f"ID: {project['id']}\n"
            f"Название: {project['name']}\n"
            f"Статус: {project['status']}\n"
            f"Начало: {project['date_start']}\n"
            f"Окончание: {project.get('date_end') or '-'}\n"
        )
        body = ttk.Frame(w, style="Surface.TFrame", padding=(16, 16))
        body.pack(fill=BOTH, expand=True)
        ttk.Label(body, text=text, justify=LEFT, style="Surface.TLabel").pack(fill=BOTH, expand=True)

    def _reset_filters(self) -> None:
        self.global_filter_context.rows = [FilterRowState(logic="AND", field="status", op="!=", value="Завершена")]
        self.global_filter_context.preset_name = DEFAULT_PRESET_NAME
        self.global_filter_context.dashboard_visible = False
        self.global_filter_context.kanban_visible = False
        self.global_filter_context.timeline_visible = False
        self.selected_project_id = None
        if hasattr(self, "top_tree"):
            self._suppress_top_select_event = True
            try:
                self.top_tree.selection_remove(*self.top_tree.selection())
            finally:
                self._suppress_top_select_event = False
        self._apply_global_filter_context_to_zone("dashboard")
        self._apply_global_filter_context_to_zone("kanban")
        self._apply_global_filter_context_to_zone("timeline")
        if hasattr(self, "preset_var"):
            self.preset_var.set(DEFAULT_PRESET_NAME)
        if hasattr(self, "kanban_preset_var"):
            self.kanban_preset_var.set(DEFAULT_PRESET_NAME)
        if hasattr(self, "analytics_preset_var"):
            self.analytics_preset_var.set(DEFAULT_PRESET_NAME)
        self._refresh_global_filter_indicators()
        self._apply_filters()
        self._refresh_kanban_board()
        self._refresh_analytics()

    def _add_filter_row(
        self, field: str = "status", op: str = "==", value: str = "", logic: str = "AND"
    ) -> None:
        row = ttk.Frame(self.rows_holder)
        row.pack(fill="x", pady=2)

        logic_var = StringVar(value=logic)
        field_var = StringVar(value=field)
        op_var = StringVar(value=op)
        value_var = StringVar(value=value)

        if self.filter_rows:
            ttk.Combobox(row, textvariable=logic_var, values=["AND", "OR"], width=6, state="readonly").pack(
                side=LEFT, padx=2
            )
        else:
            ttk.Label(row, text="").pack(side=LEFT, padx=2)

        ttk.Combobox(
            row,
            textvariable=field_var,
            values=[
                "id",
                "description",
                "status",
                "date_created",
                "date_start_work",
                "date_done",
                "executor_full_name",
                "executor_user_id",
                "customer",
                "code_link",
                "project_id",
                "project_name",
                "pocket_id",
                "pocket_name",
            ],
            width=18,
            state="readonly",
        ).pack(side=LEFT, padx=2)
        ttk.Combobox(
            row,
            textvariable=op_var,
            values=["==", "!=", "in", "contains", "between", ">", "<", ">=", "<="],
            width=10,
            state="readonly",
        ).pack(side=LEFT, padx=2)
        ttk.Entry(row, textvariable=value_var, width=36).pack(side=LEFT, padx=2)
        self._mk_button(row, "x", lambda r=row: self._remove_row(r), width=3).pack(side=LEFT, padx=2)

        self.filter_rows.append(FilterRow(row, logic_var, field_var, op_var, value_var))
        self._refresh_filter_indicator()

    def _remove_row(self, row_frame: ttk.Frame) -> None:
        for idx, item in enumerate(self.filter_rows):
            if item.frame == row_frame:
                item.frame.destroy()
                self.filter_rows.pop(idx)
                break
        self._apply_filters()

    def _add_kanban_filter_row(
        self, field: str = "executor_user_id", op: str = "==", value: str = "", logic: str = "AND"
    ) -> None:
        row = ttk.Frame(self.kanban_rows_holder)
        row.pack(fill="x", pady=2)
        logic_var = StringVar(value=logic)
        field_var = StringVar(value=field)
        op_var = StringVar(value=op)
        value_var = StringVar(value=value)

        if self.kanban_filter_rows:
            ttk.Combobox(row, textvariable=logic_var, values=["AND", "OR"], width=6, state="readonly").pack(
                side=LEFT, padx=2
            )
        else:
            ttk.Label(row, text="").pack(side=LEFT, padx=2)

        ttk.Combobox(
            row,
            textvariable=field_var,
            values=[
                "id",
                "description",
                "status",
                "date_created",
                "date_start_work",
                "date_done",
                "executor_full_name",
                "executor_user_id",
                "customer",
                "code_link",
                "project_id",
                "project_name",
                "pocket_id",
                "pocket_name",
            ],
            width=18,
            state="readonly",
        ).pack(side=LEFT, padx=2)
        ttk.Combobox(
            row,
            textvariable=op_var,
            values=["==", "!=", "in", "contains", "between", ">", "<", ">=", "<="],
            width=10,
            state="readonly",
        ).pack(side=LEFT, padx=2)
        ttk.Entry(row, textvariable=value_var, width=36).pack(side=LEFT, padx=2)
        self._mk_button(row, "x", lambda r=row: self._remove_kanban_filter_row(r), width=3).pack(side=LEFT, padx=2)

        self.kanban_filter_rows.append(FilterRow(row, logic_var, field_var, op_var, value_var))
        self._refresh_kanban_filter_indicator()

    def _remove_kanban_filter_row(self, row_frame: ttk.Frame) -> None:
        for idx, item in enumerate(self.kanban_filter_rows):
            if item.frame == row_frame:
                item.frame.destroy()
                self.kanban_filter_rows.pop(idx)
                break
        self._apply_kanban_filters()

    def _build_task_view(self, task: dict[str, Any]) -> dict[str, Any]:
        project = self.projects_by_id.get(int(task["project_id"]), {})
        pocket = self.pockets_by_id.get(int(project.get("pocket_id", 0)), {})
        executor = self.users_by_id.get(int(task.get("executor_user_id") or 0), {})
        view = dict(task)
        view["project_name"] = project.get("name", "")
        view["pocket_id"] = pocket.get("id", "")
        view["pocket_name"] = pocket.get("name", "")
        view["executor_full_name"] = executor.get("full_name", "")
        return view

    def _match_condition(self, value: Any, op: str, raw_value: str) -> bool:
        value_str = "" if value is None else str(value)
        if op == "contains":
            return raw_value.lower() in value_str.lower()
        if op == "in":
            pool = [x.strip() for x in raw_value.split(",") if x.strip()]
            return value_str in pool
        if op == "between":
            parts = [x.strip() for x in raw_value.split(",")]
            if len(parts) != 2:
                return False
            left, right = parts
            return left <= value_str <= right

        # Numeric/date compares are handled as strings if parse fails.
        left_cmp: Any = value_str
        right_cmp: Any = raw_value
        try:
            left_cmp = float(value_str)
            right_cmp = float(raw_value)
        except ValueError:
            try:
                left_cmp = date.fromisoformat(value_str)
                right_cmp = date.fromisoformat(raw_value)
            except ValueError:
                pass

        if op == "==":
            return left_cmp == right_cmp
        if op == "!=":
            return left_cmp != right_cmp
        if op == ">":
            return left_cmp > right_cmp
        if op == "<":
            return left_cmp < right_cmp
        if op == ">=":
            return left_cmp >= right_cmp
        if op == "<=":
            return left_cmp <= right_cmp
        return False

    def _apply_filters(self) -> None:
        if self._in_filter_refresh:
            return
        self._in_filter_refresh = True
        try:
            self._sync_global_filter_context_from_rows(
                self.filter_rows,
                zone="dashboard",
                preset_name=self.preset_var.get() if hasattr(self, "preset_var") else DEFAULT_PRESET_NAME,
                visible=self.filter_visible,
            )
            self._apply_global_filter_context_to_zone("kanban")
            self._apply_global_filter_context_to_zone("timeline")
            self._apply_global_filter_context_to_zone("analytics")
            if hasattr(self, "kanban_preset_var"):
                preset_name = self.global_filter_context.preset_name
                self.kanban_preset_var.set(preset_name if preset_name in self.kanban_presets else DEFAULT_PRESET_NAME)
            if "timeline_preset_var" in self.__dict__:
                preset_name = self.global_filter_context.preset_name
                self.timeline_preset_var.set(preset_name if preset_name in self.presets else DEFAULT_PRESET_NAME)
            if "analytics_preset_var" in self.__dict__:
                preset_name = self.global_filter_context.preset_name
                self.analytics_preset_var.set(preset_name if preset_name in self.presets else DEFAULT_PRESET_NAME)
            self._refresh_dashboard_top_table_from_filter_context()
            self._refresh_dashboard_bottom_table_from_selection_and_filter()
            self._refresh_kanban_board()
            self._refresh_timeline()
            self._refresh_analytics()
            self._refresh_global_filter_indicators()
        finally:
            self._in_filter_refresh = False

    def _apply_filter_rows_to_rows(self, rows: list[dict[str, Any]], filter_rows: list[FilterRow]) -> list[dict[str, Any]]:
        result = list(rows)
        for idx, cond in enumerate(filter_rows):
            field = cond.field_var.get()
            op = cond.op_var.get()
            raw = cond.value_var.get()
            if not field or not op:
                continue
            logic = cond.logic_var.get() if idx > 0 else "AND"
            source_rows = result if logic == "AND" else rows
            filtered = [r for r in source_rows if self._match_condition(r.get(field), op, raw)]
            if idx == 0 or logic == "AND":
                result = filtered
            else:
                ids = {int(r["id"]) for r in result}
                for item in filtered:
                    if int(item["id"]) not in ids:
                        result.append(item)
        return result

    def _serialize_filters(self) -> list[dict[str, str]]:
        return self._serialize_filter_rows(self.filter_rows)

    def _load_presets(self) -> dict[str, Any]:
        path = _preset_file()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        presets = {
            DEFAULT_PRESET_NAME: {
                "filter_visible": False,
                "filters": [{"logic": "AND", "field": "status", "op": "!=", "value": "Завершена"}],
            }
        }
        self._save_presets(presets)
        return presets

    def _save_presets(self, data: dict[str, Any]) -> None:
        with open(_preset_file(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _refresh_preset_combo(self) -> None:
        self.preset_combo["values"] = sorted(self.presets.keys())

    def _apply_selected_preset(self) -> None:
        name = self.preset_var.get()
        self._apply_preset(name)
        self._apply_filters()

    def _apply_preset(self, name: str) -> None:
        preset = self.presets.get(name)
        if not preset:
            return
        for row in self.filter_rows:
            row.frame.destroy()
        self.filter_rows.clear()
        for cond in preset.get("filters", []):
            self._add_filter_row(
                field=cond.get("field", "status"),
                op=cond.get("op", "=="),
                value=cond.get("value", ""),
                logic=cond.get("logic", "AND"),
            )
        self.filter_visible = bool(preset.get("filter_visible", False))
        if self.filter_visible:
            self.filter_panel.pack(fill="x", before=self.bottom_controls)
        else:
            self.filter_panel.pack_forget()
        self._sync_global_filter_context_from_rows(
            self.filter_rows,
            zone="dashboard",
            preset_name=name,
            visible=self.filter_visible,
        )
        self._apply_global_filter_context_to_zone("kanban")
        self._apply_global_filter_context_to_zone("timeline")
        self._apply_global_filter_context_to_zone("analytics")
        if hasattr(self, "kanban_preset_var"):
            self.kanban_preset_var.set(name if name in self.kanban_presets else DEFAULT_PRESET_NAME)
        if "timeline_preset_var" in self.__dict__:
            self.timeline_preset_var.set(name if name in self.presets else DEFAULT_PRESET_NAME)
        if "analytics_preset_var" in self.__dict__:
            self.analytics_preset_var.set(name if name in self.presets else DEFAULT_PRESET_NAME)

    def _save_current_preset(self) -> None:
        name = simpledialog.askstring("Сохранить пресет", "Имя пресета:", parent=self)
        if not name:
            return
        self.presets[name] = {
            "filter_visible": self.filter_visible,
            "filters": self._serialize_filters(),
        }
        self._save_presets(self.presets)
        self._refresh_preset_combo()
        self.preset_var.set(name)

    def _rename_preset(self) -> None:
        old = self.preset_var.get()
        if old not in self.presets:
            return
        new = simpledialog.askstring("Переименовать пресет", "Новое имя:", initialvalue=old, parent=self)
        if not new or new == old:
            return
        self.presets[new] = self.presets.pop(old)
        self._save_presets(self.presets)
        self._refresh_preset_combo()
        self.preset_var.set(new)

    def _delete_preset(self) -> None:
        name = self.preset_var.get()
        if name == DEFAULT_PRESET_NAME:
            messagebox.showwarning("Ограничение", "Пресет по умолчанию удалить нельзя.")
            return
        if name in self.presets:
            del self.presets[name]
            self._save_presets(self.presets)
            self._refresh_preset_combo()
            self.preset_var.set(DEFAULT_PRESET_NAME)
            self._apply_preset(DEFAULT_PRESET_NAME)
            self._apply_filters()

    def _load_kanban_presets(self) -> dict[str, Any]:
        path = _kanban_preset_file()
        default_filters = [
            {"logic": "AND", "field": "status", "op": "!=", "value": "\u0417\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0430"},
        ]
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    data[DEFAULT_PRESET_NAME] = {
                        "filter_visible": bool(data.get(DEFAULT_PRESET_NAME, {}).get("filter_visible", False)),
                        "filters": default_filters,
                    }
                    self._save_kanban_presets(data)
                    return data
        presets = {
            DEFAULT_PRESET_NAME: {
                "filter_visible": False,
                "filters": default_filters,
            }
        }
        self._save_kanban_presets(presets)
        return presets

    def _save_kanban_presets(self, data: dict[str, Any]) -> None:
        with open(_kanban_preset_file(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _refresh_kanban_preset_combo(self) -> None:
        self.kanban_preset_combo["values"] = sorted(self.kanban_presets.keys())

    def _apply_selected_kanban_preset(self) -> None:
        self._apply_kanban_preset(self.kanban_preset_var.get())
        self._refresh_kanban_board()

    def _apply_kanban_preset(self, name: str) -> None:
        preset = self.kanban_presets.get(name)
        if not preset:
            return
        for row in self.kanban_filter_rows:
            row.frame.destroy()
        self.kanban_filter_rows.clear()
        for cond in preset.get("filters", []):
            self._add_kanban_filter_row(
                field=cond.get("field", "executor_user_id"),
                op=cond.get("op", "=="),
                value=cond.get("value", ""),
                logic=cond.get("logic", "AND"),
            )
        self.kanban_filter_visible = bool(preset.get("filter_visible", False))
        if self.kanban_filter_visible:
            self.kanban_filter_panel.pack(fill="x", before=self.kanban_bottom_controls)
        else:
            self.kanban_filter_panel.pack_forget()
        self._sync_global_filter_context_from_rows(
            self.kanban_filter_rows,
            zone="kanban",
            preset_name=name,
            visible=self.kanban_filter_visible,
        )
        self._apply_global_filter_context_to_zone("dashboard")
        self._apply_global_filter_context_to_zone("timeline")
        if hasattr(self, "preset_var"):
            self.preset_var.set(name if name in self.presets else DEFAULT_PRESET_NAME)
        if "timeline_preset_var" in self.__dict__:
            self.timeline_preset_var.set(name if name in self.presets else DEFAULT_PRESET_NAME)

    def _serialize_kanban_filters(self) -> list[dict[str, str]]:
        return self._serialize_filter_rows(self.kanban_filter_rows)

    def _save_current_kanban_preset(self) -> None:
        name = simpledialog.askstring("Сохранить пресет", "Имя пресета:", parent=self)
        if not name:
            return
        self.kanban_presets[name] = {
            "filter_visible": self.kanban_filter_visible,
            "filters": self._serialize_kanban_filters(),
        }
        self._save_kanban_presets(self.kanban_presets)
        self._refresh_kanban_preset_combo()
        self.kanban_preset_var.set(name)

    def _rename_kanban_preset(self) -> None:
        old = self.kanban_preset_var.get()
        if old not in self.kanban_presets:
            return
        new = simpledialog.askstring("Переименовать пресет", "Новое имя:", initialvalue=old, parent=self)
        if not new or new == old:
            return
        self.kanban_presets[new] = self.kanban_presets.pop(old)
        self._save_kanban_presets(self.kanban_presets)
        self._refresh_kanban_preset_combo()
        self.kanban_preset_var.set(new)

    def _delete_kanban_preset(self) -> None:
        name = self.kanban_preset_var.get()
        if name == DEFAULT_PRESET_NAME:
            messagebox.showwarning("Ограничение", "Пресет по умолчанию удалить нельзя.")
            return
        if name in self.kanban_presets:
            del self.kanban_presets[name]
            self._save_kanban_presets(self.kanban_presets)
            self._refresh_kanban_preset_combo()
            self.kanban_preset_var.set(DEFAULT_PRESET_NAME)
            self._apply_kanban_preset(DEFAULT_PRESET_NAME)
            self._refresh_kanban_board()

    def _open_user_guide_window(self) -> None:
        if self.user_guide_window and self.user_guide_window.winfo_exists():
            self.user_guide_window.lift()
            self.user_guide_window.focus_force()
            return

        w = self._create_popup(self)
        w.title("Руководство пользователя")
        w.geometry("980x700")
        self.user_guide_window = w
        w.protocol("WM_DELETE_WINDOW", self._close_user_guide_window)

        root = ttk.Frame(w, style="Surface.TFrame", padding=(10, 10))
        root.pack(fill=BOTH, expand=True)
        notebook = ttk.Notebook(root)
        notebook.pack(fill=BOTH, expand=True)

        quick_start = (
            "1. Запустите API и приложение.\n"
            "2. При старте используется логин ОС для входа в API.\n"
            "3. Переключайте зоны: Дэшборд, Канбан, Timeline, Аналитика.\n"
            "4. Базовый фильтр по умолчанию: статус != Завершена.\n\n"
            "Роли:\n"
            "- admin, head: полный доступ.\n"
            "- curator: чтение всей картины + изменения в своем контуре.\n"
            "- executor: рабочие действия по задачам.\n"
        )
        self._add_guide_tab(notebook, "Быстрый старт", quick_start)

        dashboard_text = (
            "Дэшборд состоит из двух таблиц:\n"
            "- Верхняя: карман + проект.\n"
            "- Нижняя: задачи.\n\n"
            "Логика:\n"
            "- Выбор проекта в верхней таблице добавляет системное условие project_id == X.\n"
            "- Условие влияет на все зоны.\n"
            "- Двойной клик по проекту/задаче открывает форму редактирования.\n"
        )
        self._add_guide_tab(notebook, "Дэшборд", dashboard_text)

        kanban_text = (
            "Колонки Канбан:\n"
            "- Очередь: Создана и исполнитель не назначен.\n"
            "- Создана: Создана и исполнитель назначен.\n"
            "- В работе / Приостановлена / Завершена.\n\n"
            "Действия:\n"
            "- Назначить: назначение без старта.\n"
            "- Старт, Пауза, Возобновить, Завершить.\n\n"
            "Двойной клик по карточке открывает задачу.\n"
        )
        self._add_guide_tab(notebook, "Канбан", kanban_text)

        timeline_text = (
            "Timeline = таблица + гантт.\n"
            "- Вертикальный скролл синхронный.\n"
            "- Горизонтальный скролл только у гантта.\n"
            "- Период (Начало/Окончание) применяется только к Timeline.\n"
            "- В таблице описание сокращается до 40 символов, полный текст по наведению.\n"
            "- Разделитель между таблицей и ганттом можно двигать.\n"
        )
        self._add_guide_tab(notebook, "Timeline", timeline_text)

        analytics_text = (
            "Аналитика использует тот же глобальный фильтр.\n"
            "Показатели:\n"
            "- Распределение по статусам\n"
            "- WIP по исполнителям\n"
            "- Пропускная способность по неделям\n"
            "- Cycle time по проектам\n"
            "- Lead time по карманам\n"
            "- Просроченные задачи\n"
            "- Доля пауз по исполнителям\n"
            "- Возраст очереди\n\n"
            "Клик по строке показателя включает детализацию и обновляет все зоны.\n"
            "Кнопка «Снять детализацию» убирает drill-down слой.\n"
        )
        self._add_guide_tab(notebook, "Аналитика", analytics_text)

        refs_text = (
            "Справочники:\n"
            "- Карманы, Проекты, Задачи, Пользователи, Статусы.\n"
            "- Открываются в popup-окнах.\n"
            "- В таблицах доступен двойной клик для редактирования.\n\n"
            "Настройки БД:\n"
            "- Настройки -> База данных.\n"
            "- sqlite / postgres-greenplum (заглушка).\n\n"
            "Экспорт:\n"
            "- CSV резерв исходных данных.\n"
            "- Excel: одна строка = одна задача.\n"
        )
        self._add_guide_tab(notebook, "Справочники и сервис", refs_text)

        footer = ttk.Frame(root)
        footer.pack(fill="x", pady=(8, 0))
        self._mk_button(footer, "Закрыть", self._close_user_guide_window).pack(side=RIGHT)

    def _add_guide_tab(self, notebook: ttk.Notebook, title: str, content: str) -> None:
        tab = ttk.Frame(notebook, style="Surface.TFrame")
        notebook.add(tab, text=title)
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        holder = ttk.Frame(tab, style="Surface.TFrame")
        holder.grid(row=0, column=0, sticky="nsew")
        canvas = Canvas(holder, highlightthickness=0, bd=0, bg=self._theme_color("surface_panel", "#FFFFFF"))
        yscroll = ttk.Scrollbar(holder, orient=VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=yscroll.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        yscroll.pack(side=RIGHT, fill="y")

        inner = ttk.Frame(canvas, style="Surface.TFrame", padding=(14, 14))
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda _e, c=canvas: c.configure(scrollregion=c.bbox("all")))
        canvas.bind("<Configure>", lambda e, c=canvas, wid=window_id: c.itemconfigure(wid, width=max(1, int(getattr(e, "width", 1)))))
        ttk.Label(inner, text=content, style="Surface.TLabel", justify=LEFT).pack(fill=BOTH, expand=True)

    def _close_user_guide_window(self) -> None:
        if self.user_guide_window and self.user_guide_window.winfo_exists():
            self.user_guide_window.destroy()
        self.user_guide_window = None

    def _show_about(self) -> None:
        w = self._create_popup(self)
        w.title("О программе")
        w.geometry("520x320")
        body = ttk.Frame(w, style="Surface.TFrame", padding=(16, 16))
        body.pack(fill=BOTH, expand=True)

        logo_path = _app_logo_file()
        if os.path.exists(logo_path):
            try:
                if Image is not None and ImageTk is not None:
                    img = Image.open(logo_path)
                    img.thumbnail((170, 110))
                    self._about_logo_image = ImageTk.PhotoImage(img)
                else:
                    raw = PhotoImage(file=logo_path)
                    subsample = max(1, int(max(raw.width() / 170, raw.height() / 110)))
                    self._about_logo_image = raw.subsample(subsample, subsample)
                ttk.Label(body, image=self._about_logo_image, style="Surface.TLabel").pack(pady=(0, 12))
            except Exception:
                self._about_logo_image = None

        text = (
            "PocketFlow\n"
            "Desktop workflow manager (Tkinter MVP)\n\n"
            "Зоны: Дэшборд, Канбан, Timeline, Аналитика\n"
            "Справочники: Карманы, Проекты, Задачи, Пользователи, Статусы\n"
            "Экспорт: CSV резерв и Excel по задачам"
        )
        ttk.Label(body, text=text, justify=LEFT, style="Surface.TLabel").pack(fill=BOTH, expand=True)
        self._mk_button(body, "Закрыть", w.destroy).pack(anchor="e", pady=(10, 0))

    def _show_theme_info(self) -> None:
        theme_file = _theme_file(self.theme_name)
        base_ttk = str(self.theme_tokens.get("base_ttk_theme", "forest-light"))
        messagebox.showinfo(
            "Тема интерфейса",
            (
                f"Активная тема: {self.theme_name}\n"
                f"JSON темы: {theme_file}\n"
                f"Базовая ttk-тема: {base_ttk}\n"
                "Тема сохраняется в локальном ui_config.json."
            ),
        )

    def _on_theme_selected(self) -> None:
        self._toggle_theme()

    def _theme_button_text(self) -> str:
        return "Тема: Светлая" if self.theme_name == "forest-light" else "Тема: Тёмная"

    def _toggle_theme(self) -> None:
        messagebox.showinfo("Тема", "Переключение темы временно отключено. Используется светлая тема.")

    def _set_theme(self, theme_name: str) -> None:
        tokens = self._load_theme_tokens_with_fallback(theme_name)
        new_theme_name = str(tokens.get("id", DEFAULT_THEME_NAME))
        if new_theme_name == self.theme_name and self.theme_tokens == tokens:
            return
        self.theme_tokens = tokens
        self.theme_name = new_theme_name
        self.theme_var.set(self.theme_name)
        self.role_colors = self._role_palette_for_theme(self.theme_name)
        self._save_theme_name(self.theme_name)
        self._rebuild_ui()

    def _theme_in_development(self) -> None:
        self._toggle_theme()

    def _resolve_kanban_icon_paths(self, theme_name: str) -> dict[str, str]:
        _ = theme_name
        icon_cfg = self.theme_tokens.get("icons", {}) if isinstance(self.theme_tokens, dict) else {}
        palette = str(icon_cfg.get("palette", "light"))
        source_dir = _icons_source_dir(palette)
        paths: dict[str, str] = {}
        missing: list[str] = []
        for action_key, filename in KANBAN_ACTION_ICONS.items():
            path = os.path.join(source_dir, f"{filename}.png")
            if not os.path.exists(path):
                missing.append(path)
            else:
                paths[action_key] = path
        if missing:
            raise FileNotFoundError("Missing icon files: " + ", ".join(missing))
        return paths

    def _load_kanban_icons(self, theme_name: str) -> None:
        self.icon_images = {}
        try:
            icon_paths = self._resolve_kanban_icon_paths(theme_name)
            for action_key, path in icon_paths.items():
                self.icon_images[action_key] = PhotoImage(file=path)
        except Exception as exc:
            self.icon_images = {}
            if not self._icon_error_shown:
                self._icon_error_shown = True
                messagebox.showerror("Иконки Kanban", f"Иконки не загружены: {exc}")

    def _ensure_kanban_icons_ready(self) -> None:
        required = set(KANBAN_ACTION_ICONS.keys())
        if required.issubset(set(self.icon_images.keys())):
            return
        self._load_kanban_icons(self.theme_name)

    def _mk_button(self, parent: ttk.Frame, text: str, command: Any, **kwargs: Any) -> ttk.Button:
        btn = ttk.Button(
            parent,
            text=text,
            command=command,
            **kwargs,
        )
        return btn

    def _mk_vendor_option_menu(self, title: str, items: list[str]) -> None:
        var = StringVar(value=title)
        self._menu_vars.append(var)
        opt = ttk.OptionMenu(
            self.menu_bar,
            var,
            title,
            *items,
            command=lambda selected, v=var, t=title: self._on_menu_option_selected(selected, v, t),
            style="TOptionMenu",
        )
        opt.configure(width=20)
        menu_widget = self.nametowidget(opt["menu"])
        menu_widget.configure(
            tearoff=False,
            bg=self._theme_color("surface_panel", "#ffffff"),
            fg=self._theme_color("text_primary", "#1f2328"),
            activebackground=self._theme_color("accent", "#4F6B5A"),
            activeforeground=self._theme_color("selection_fg", "#ffffff"),
        )
        opt.pack(side=LEFT, padx=2)

    def _on_menu_option_selected(self, selected: str, var: StringVar, title: str) -> None:
        if selected != title:
            action = self._menu_actions.get(selected)
            if action:
                action()
        var.set(title)

    def _autosize_tree_columns(
        self,
        tree: ttk.Treeview,
        columns: tuple[str, ...],
        rows: list[tuple[Any, ...]],
        min_width: int = 80,
        max_width_overrides: dict[str, int] | None = None,
    ) -> None:
        font = tkfont.nametofont("TkDefaultFont")
        max_widths = max_width_overrides or {}
        sample_rows = rows[:300]
        for idx, col in enumerate(columns):
            title = str(tree.heading(col, "text"))
            width = font.measure(title) + 24
            for row in sample_rows:
                value = "" if idx >= len(row) or row[idx] is None else str(row[idx])
                width = max(width, font.measure(value) + 24)
            max_width = max_widths.get(col, 240)
            tree.column(col, width=max(min_width, min(width, max_width)))

    def _format_filter_text(self) -> str:
        return self._format_filter_text_for_rows(self.filter_rows)

    def _format_filter_text_for_rows(self, rows: list[FilterRow]) -> str:
        parts: list[str] = []
        for idx, cond in enumerate(rows):
            field = cond.field_var.get().strip()
            op = cond.op_var.get().strip()
            value = cond.value_var.get().strip()
            if not field or not op:
                continue
            clause = f"{field} {op} {value}".strip()
            if idx > 0:
                clause = f"{cond.logic_var.get()} {clause}"
            parts.append(clause)
        if not parts:
            return "Фильтр пуст"
        return " ".join(parts)

    def _refresh_filter_indicator(self) -> None:
        self._refresh_global_filter_indicators()

    def _refresh_kanban_filter_indicator(self) -> None:
        self._refresh_global_filter_indicators()

    def _show_filter_tooltip(self, _event: object) -> None:
        self._hide_filter_tooltip()
        if not self._filter_summary_full_text:
            return
        x = self.filter_summary_label.winfo_rootx()
        y = self.filter_summary_label.winfo_rooty() - 30
        tip = Toplevel(self)
        tip.overrideredirect(True)
        tip.geometry(f"+{x}+{y}")
        tip.attributes("-topmost", True)
        ttk.Label(tip, text=self._filter_summary_full_text, style="Surface.TLabel", padding=(8, 4)).pack()
        self._filter_tooltip = tip

    def _hide_filter_tooltip(self, _event: object | None = None) -> None:
        if self._filter_tooltip and self._filter_tooltip.winfo_exists():
            self._filter_tooltip.destroy()
        self._filter_tooltip = None

    def _attach_tooltip(self, widget: ttk.Widget, text: str) -> None:
        widget.bind("<Enter>", lambda event, tooltip_text=text: self._show_widget_tooltip(event, tooltip_text))
        widget.bind("<Leave>", self._hide_widget_tooltip)
        widget.bind("<ButtonPress>", self._hide_widget_tooltip)

    def _show_widget_tooltip(self, event: object, text: str) -> None:
        if not text:
            return
        self._hide_widget_tooltip()
        widget = event.widget  # type: ignore[attr-defined]
        x = widget.winfo_rootx() + 8
        y = widget.winfo_rooty() - 30
        tip = Toplevel(self)
        tip.overrideredirect(True)
        tip.geometry(f"+{x}+{y}")
        tip.attributes("-topmost", True)
        ttk.Label(tip, text=text, style="Surface.TLabel", padding=(8, 4)).pack()
        self._widget_tooltip = tip

    def _hide_widget_tooltip(self, _event: object | None = None) -> None:
        tip = self.__dict__.get("_widget_tooltip")
        if tip and tip.winfo_exists():
            tip.destroy()
        self._widget_tooltip = None
        if hasattr(self, "_timeline_hover_task_id"):
            self._timeline_hover_task_id = None

    def _show_kanban_filter_tooltip(self, _event: object) -> None:
        self._hide_kanban_filter_tooltip()
        if not self._kanban_filter_summary_full_text:
            return
        x = self.kanban_filter_label.winfo_rootx()
        y = self.kanban_filter_label.winfo_rooty() - 30
        tip = Toplevel(self)
        tip.overrideredirect(True)
        tip.geometry(f"+{x}+{y}")
        tip.attributes("-topmost", True)
        ttk.Label(tip, text=self._kanban_filter_summary_full_text, style="Surface.TLabel", padding=(8, 4)).pack()
        self._kanban_filter_tooltip = tip

    def _hide_kanban_filter_tooltip(self, _event: object | None = None) -> None:
        if self._kanban_filter_tooltip and self._kanban_filter_tooltip.winfo_exists():
            self._kanban_filter_tooltip.destroy()
        self._kanban_filter_tooltip = None

    def _rebuild_ui(self) -> None:
        self._hide_filter_tooltip()
        self._hide_kanban_filter_tooltip()
        self._hide_widget_tooltip()
        self._close_pockets_window()
        self._close_projects_window()
        self._close_tasks_window()
        self._close_users_window()
        self._close_statuses_window()
        self._close_db_settings_window()
        self._close_user_guide_window()
        for child in self.winfo_children():
            child.destroy()
        self.session_user = None
        self._setup_forest_theme()
        self._apply_theme_settings()
        self._build_menu()
        self._build_ribbon()
        self._build_zones()
        self._show_zone(self.current_zone if self.current_zone in self.zones else "dashboard")
        self._load_dashboard_data()

    def _load_theme_name(self) -> str:
        return DEFAULT_THEME_NAME

    def _save_theme_name(self, theme_name: str) -> None:
        path = _ui_config_file()
        data: dict[str, Any] = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        data = loaded
            except Exception:
                data = {}
        data["theme"] = theme_name
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_db_settings(self) -> dict[str, str]:
        path = _ui_config_file()
        default_path = os.path.abspath("kanban.db")
        settings = {
            "db_type": "sqlite",
            "db_value": default_path,
        }
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    db_type = str(loaded.get("db_type", settings["db_type"])).strip().lower()
                    db_value = str(loaded.get("db_value", settings["db_value"])).strip()
                    if db_type not in {"sqlite", "postgres/greenplum"}:
                        db_type = "sqlite"
                    settings["db_type"] = db_type
                    settings["db_value"] = db_value or settings["db_value"]
            except Exception:
                pass
        return settings

    def _save_db_settings(self, db_type: str, db_value: str) -> None:
        path = _ui_config_file()
        data: dict[str, Any] = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    data = loaded
            except Exception:
                data = {}
        data["db_type"] = db_type
        data["db_value"] = db_value
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _open_db_settings_window(self) -> None:
        if self.db_settings_window and self.db_settings_window.winfo_exists():
            self.db_settings_window.lift()
            self.db_settings_window.focus_force()
            return

        w = self._create_popup(self)
        w.title("Настройки БД")
        w.geometry("620x230")
        self.db_settings_window = w
        w.protocol("WM_DELETE_WINDOW", lambda: self._close_db_settings_window())

        body = ttk.Frame(w, style="Surface.TFrame", padding=(14, 14))
        body.pack(fill=BOTH, expand=True)
        body.grid_columnconfigure(1, weight=1)

        db_type_var = StringVar(value=self.db_settings.get("db_type", "sqlite"))
        db_value_var = StringVar(value=self.db_settings.get("db_value", os.path.abspath("kanban.db")))
        field_label_var = StringVar(value="Путь к файлу SQLite")
        hint_var = StringVar(value="")

        ttk.Label(body, text="Тип БД:").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=6)
        db_type_combo = ttk.Combobox(
            body,
            textvariable=db_type_var,
            values=["sqlite", "postgres/greenplum"],
            state="readonly",
            width=26,
        )
        db_type_combo.grid(row=0, column=1, sticky="w", pady=6)

        ttk.Label(body, textvariable=field_label_var).grid(row=1, column=0, sticky="w", padx=(0, 8), pady=6)
        value_entry = ttk.Entry(body, textvariable=db_value_var)
        value_entry.grid(row=1, column=1, sticky="ew", pady=6)

        hint = ttk.Label(body, textvariable=hint_var, style="Surface.TLabel")
        hint.grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 10))

        def refresh_db_form(*_args: Any) -> None:
            selected = db_type_var.get().strip().lower()
            if selected == "sqlite":
                field_label_var.set("Путь к файлу SQLite")
                hint_var.set("Укажите путь к .db файлу. Пример: D:\\data\\kanban.db")
                value_entry.state(["!disabled"])
            else:
                field_label_var.set("Конфигурация подключения")
                hint_var.set("Postgres/Greenplum: заглушка, подключение пока не реализовано.")
                value_entry.state(["!disabled"])

        db_type_combo.bind("<<ComboboxSelected>>", refresh_db_form)
        refresh_db_form()

        buttons = ttk.Frame(body)
        buttons.grid(row=3, column=0, columnspan=2, sticky="e", pady=(12, 0))

        def save_db_settings() -> None:
            selected = db_type_var.get().strip().lower()
            value = db_value_var.get().strip()
            if selected == "sqlite":
                if not value:
                    messagebox.showwarning("Настройки БД", "Укажите путь к файлу SQLite.", parent=w)
                    return
                value = os.path.abspath(value)
                db_value_var.set(value)
                self.db_settings = {"db_type": selected, "db_value": value}
                self._save_db_settings(selected, value)
                os.environ["KANBAN_DB_PATH"] = value
                messagebox.showinfo("Настройки БД", "Параметры SQLite сохранены.", parent=w)
                return
            self.db_settings = {"db_type": selected, "db_value": value}
            self._save_db_settings(selected, value)
            messagebox.showinfo("Настройки БД", "Режим Postgres/Greenplum сохранен как заглушка.", parent=w)

        self._mk_button(buttons, "Сохранить", save_db_settings).pack(side=LEFT, padx=6)
        self._mk_button(buttons, "Закрыть", self._close_db_settings_window).pack(side=LEFT, padx=6)

    def _close_db_settings_window(self) -> None:
        if self.db_settings_window and self.db_settings_window.winfo_exists():
            self.db_settings_window.destroy()
        self.db_settings_window = None

    def _open_export_window(self) -> None:
        w = self._create_popup(self)
        w.title("Экспорт данных")
        w.geometry("760x260")

        body = ttk.Frame(w, style="Surface.TFrame", padding=(14, 14))
        body.pack(fill=BOTH, expand=True)
        body.grid_columnconfigure(1, weight=1)

        backup_dir_var = StringVar(value=str(Path.cwd() / "exports"))
        xlsx_path_var = StringVar(value=str(Path.cwd() / "exports" / f"tasks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"))

        ttk.Label(body, text="CSV резерв (папка):").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=6)
        ttk.Entry(body, textvariable=backup_dir_var).grid(row=0, column=1, sticky="ew", pady=6)
        self._mk_button(body, "...", lambda: self._pick_export_dir(backup_dir_var), width=4).grid(row=0, column=2, padx=(6, 0), pady=6)

        ttk.Label(body, text="Excel файл (.xlsx):").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=6)
        ttk.Entry(body, textvariable=xlsx_path_var).grid(row=1, column=1, sticky="ew", pady=6)
        self._mk_button(body, "...", lambda: self._pick_export_xlsx(xlsx_path_var), width=4).grid(row=1, column=2, padx=(6, 0), pady=6)

        note = (
            "1) CSV резерв: исходные данные таблиц API (users/pockets/projects/tasks/task_pauses/statuses).\n"
            "2) Excel: одна строка = одна задача, с основными бизнес-сущностями."
        )
        ttk.Label(body, text=note, style="Surface.TLabel", justify=LEFT).grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 10))

        actions = ttk.Frame(body)
        actions.grid(row=3, column=0, columnspan=3, sticky="e")
        self._mk_button(actions, "Экспорт CSV", lambda: self._export_raw_csv_backup(backup_dir_var.get().strip(), parent=w)).pack(side=LEFT, padx=4)
        self._mk_button(actions, "Экспорт Excel", lambda: self._export_tasks_xlsx(xlsx_path_var.get().strip(), parent=w)).pack(side=LEFT, padx=4)
        self._mk_button(actions, "Закрыть", w.destroy).pack(side=LEFT, padx=4)

    def _pick_export_dir(self, var: StringVar) -> None:
        selected = filedialog.askdirectory(title="Папка для CSV резерва")
        if selected:
            var.set(selected)

    def _pick_export_xlsx(self, var: StringVar) -> None:
        selected = filedialog.asksaveasfilename(
            title="Файл Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx"), ("All files", "*.*")],
        )
        if selected:
            var.set(selected)

    def _export_raw_csv_backup(self, base_dir: str, *, parent: Toplevel | Tk) -> None:
        if not base_dir:
            messagebox.showwarning("Экспорт", "Укажите папку для резервной CSV копии.", parent=parent)
            return
        try:
            export_root = Path(base_dir).expanduser().resolve()
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target = export_root / f"raw_backup_{stamp}"
            target.mkdir(parents=True, exist_ok=True)

            data_map: dict[str, list[dict[str, Any]]] = {
                "users": self.api.list_users(),
                "pockets": self.api.list_pockets(),
                "projects": self.api.list_projects(),
                "tasks": self.api.list_tasks(),
                "task_pauses": self.api.list_task_pauses(),
                "statuses": self.api.list_statuses(entity_type=None, is_active=None),
            }
            for table_name, rows in data_map.items():
                self._write_rows_csv(target / f"{table_name}.csv", rows)
        except ApiClientError as exc:
            messagebox.showerror("Экспорт", f"Ошибка API при выгрузке CSV.\n{exc}", parent=parent)
            return
        except Exception as exc:
            messagebox.showerror("Экспорт", f"Не удалось сохранить CSV резерв.\n{exc}", parent=parent)
            return
        messagebox.showinfo("Экспорт", f"CSV резерв сохранен:\n{target}", parent=parent)

    def _write_rows_csv(self, path: Path, rows: list[dict[str, Any]]) -> None:
        keys: list[str] = []
        for row in rows:
            for key in row.keys():
                if key not in keys:
                    keys.append(str(key))
        if not keys:
            keys = ["empty"]
            rows = [{"empty": ""}]
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in keys})

    def _export_tasks_xlsx(self, file_path: str, *, parent: Toplevel | Tk) -> None:
        if Workbook is None:
            messagebox.showerror("Экспорт", "Модуль openpyxl не установлен. Добавьте зависимость для экспорта в XLSX.", parent=parent)
            return
        if not file_path:
            messagebox.showwarning("Экспорт", "Укажите путь к файлу Excel.", parent=parent)
            return
        try:
            if self.session_user is None or not self.tasks_all:
                self._load_dashboard_data()
            rows = [self._build_task_view(task) for task in self.tasks_all]
            wb = Workbook()
            ws = wb.active
            ws.title = "Задачи"

            headers = [
                ("task_id", "ID задачи"),
                ("description", "Описание"),
                ("status", "Статус"),
                ("date_created", "Создана"),
                ("date_start_work", "Старт работы"),
                ("date_done", "Завершена"),
                ("executor_user_id", "ID исполнителя"),
                ("executor_full_name", "Исполнитель"),
                ("customer", "Заказчик"),
                ("code_link", "Код/ссылка"),
                ("project_id", "ID проекта"),
                ("project_name", "Проект"),
                ("project_code", "Код проекта"),
                ("pocket_id", "ID кармана"),
                ("pocket_name", "Карман"),
            ]
            ws.append([h[1] for h in headers])
            for row in rows:
                project = self.projects_by_id.get(int(row.get("project_id") or 0), {})
                ws.append(
                    [
                        row.get("id", ""),
                        row.get("description", ""),
                        row.get("status", ""),
                        row.get("date_created", ""),
                        row.get("date_start_work", ""),
                        row.get("date_done", ""),
                        row.get("executor_user_id", ""),
                        row.get("executor_full_name", ""),
                        row.get("customer", ""),
                        row.get("code_link", ""),
                        row.get("project_id", ""),
                        row.get("project_name", ""),
                        project.get("project_code", ""),
                        row.get("pocket_id", ""),
                        row.get("pocket_name", ""),
                    ]
                )
            target = Path(file_path).expanduser().resolve()
            target.parent.mkdir(parents=True, exist_ok=True)
            wb.save(str(target))
        except ApiClientError as exc:
            messagebox.showerror("Экспорт", f"Ошибка API при выгрузке Excel.\n{exc}", parent=parent)
            return
        except Exception as exc:
            messagebox.showerror("Экспорт", f"Не удалось сохранить Excel файл.\n{exc}", parent=parent)
            return
        messagebox.showinfo("Экспорт", f"Excel файл сохранен:\n{target}", parent=parent)

    def _load_theme_tokens(self, theme_name: str) -> dict[str, Any]:
        path = _theme_file(theme_name)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("Theme JSON must be an object")
        for key in ("id", "base_ttk_theme", "colors", "roles", "icons"):
            if key not in data:
                raise ValueError(f"Theme missing required key: {key}")
        if not isinstance(data["colors"], dict) or not isinstance(data["roles"], dict) or not isinstance(data["icons"], dict):
            raise ValueError("Theme keys colors/roles/icons must be objects")
        return data

    def _load_theme_tokens_with_fallback(self, theme_name: str) -> dict[str, Any]:
        try:
            return self._load_theme_tokens(theme_name)
        except Exception:
            try:
                return self._load_theme_tokens(DEFAULT_THEME_NAME)
            except Exception:
                return dict(DEFAULT_THEME_TOKENS)

    def _theme_color(self, key: str, default: str) -> str:
        colors = self.theme_tokens.get("colors", {}) if isinstance(self.theme_tokens, dict) else {}
        value = colors.get(key, default)
        return str(value) if value else default

    def _role_palette_for_theme(self, theme_name: str) -> dict[str, str]:
        _ = theme_name
        roles = self.theme_tokens.get("roles", {}) if isinstance(self.theme_tokens, dict) else {}
        fallback_roles = DEFAULT_THEME_TOKENS["roles"]
        merged = dict(fallback_roles)
        if isinstance(roles, dict):
            for key, value in roles.items():
                merged[str(key)] = str(value)
        return merged

    def _apply_theme_settings(self) -> None:
        style = ttk.Style(self)
        style.configure("Session.TLabel", foreground=self.role_colors.get("executor", self._theme_color("text_muted", "#5F6B6D")))
        style.configure("TFrame", background=self._theme_color("surface_bg", "#F7F8F5"))
        style.configure("Surface.TFrame", background=self._theme_color("surface_panel", "#FFFFFF"))
        style.configure("TLabel", background=self._theme_color("surface_bg", "#F7F8F5"), foreground=self._theme_color("text_primary", "#1F2A2A"))
        style.configure("Surface.TLabel", background=self._theme_color("surface_panel", "#FFFFFF"), foreground=self._theme_color("text_primary", "#1F2A2A"))
        style.configure("TLabelframe", background=self._theme_color("surface_bg", "#F7F8F5"), bordercolor=self._theme_color("border", "#D8DDD8"))
        style.configure("TLabelframe.Label", background=self._theme_color("surface_bg", "#F7F8F5"), foreground=self._theme_color("text_primary", "#1F2A2A"))
        style.configure("KanbanColumn.TLabelframe", background=self._theme_color("surface_bg", "#F7F8F5"), bordercolor=self._theme_color("border", "#D8DDD8"))
        style.configure("KanbanColumn.TLabelframe.Label", background=self._theme_color("surface_bg", "#F7F8F5"), foreground=self._theme_color("text_primary", "#1F2A2A"))
        style.configure("Treeview", background=self._theme_color("surface_panel", "#FFFFFF"), fieldbackground=self._theme_color("surface_panel", "#FFFFFF"), foreground=self._theme_color("text_primary", "#1F2A2A"))
        style.configure("Timeline.Treeview", rowheight=TIMELINE_ROW_HEIGHT)
        style.map("Timeline.Treeview", background=[("selected", self._theme_color("selection_bg", "#6E8B74"))], foreground=[("selected", self._theme_color("selection_fg", "#FFFFFF"))])
        style.map("Treeview", background=[("selected", self._theme_color("selection_bg", "#6E8B74"))], foreground=[("selected", self._theme_color("selection_fg", "#FFFFFF"))])
        style.configure("TEntry", fieldbackground=self._theme_color("surface_panel", "#FFFFFF"), foreground=self._theme_color("text_primary", "#1F2A2A"))
        style.configure("TCombobox", fieldbackground=self._theme_color("surface_panel", "#FFFFFF"), foreground=self._theme_color("text_primary", "#1F2A2A"))
        base_font = tkfont.nametofont("TkDefaultFont")
        self.kanban_action_font = tkfont.Font(
            family=base_font.actual("family"),
            size=max(13, int(base_font.actual("size")) + 3),
            weight="bold",
        )
        style.configure("KanbanAction.TButton", font=self.kanban_action_font, padding=(6, 4), background=self._theme_color("surface_panel", "#FFFFFF"))
        style.map("KanbanAction.TButton", background=[("active", self._theme_color("accent_hover", "#3F594A"))], foreground=[("active", self._theme_color("selection_fg", "#FFFFFF"))])
        self.option_add("*TCombobox*Listbox.background", self._theme_color("surface_panel", "#FFFFFF"))
        self.option_add("*TCombobox*Listbox.foreground", self._theme_color("text_primary", "#1F2A2A"))
        self.option_add("*TCombobox*Listbox.selectBackground", self._theme_color("selection_bg", "#6E8B74"))
        self.option_add("*TCombobox*Listbox.selectForeground", self._theme_color("selection_fg", "#FFFFFF"))
        for canvas in getattr(self, "kanban_column_canvases", {}).values():
            canvas.configure(bg=self._theme_color("surface_bg", "#F7F8F5"))
        if hasattr(self, "timeline_canvas") and self.timeline_canvas:
            self.timeline_canvas.configure(bg=self._theme_color("surface_panel", "#FFFFFF"))
        if hasattr(self, "analytics_content_canvas") and self.analytics_content_canvas:
            self.analytics_content_canvas.configure(bg=self._theme_color("surface_bg", "#F7F8F5"))
        for canvas in getattr(self, "analytics_charts", {}).values():
            canvas.configure(bg=self._theme_color("surface_panel", "#FFFFFF"))
        self._load_kanban_icons(self.theme_name)

    def _setup_forest_theme(self) -> None:
        style = ttk.Style(self)
        try:
            self.tk.call("source", _forest_theme_file("forest-light").replace("\\", "/"))
            self.tk.call("source", _forest_theme_file("forest-dark").replace("\\", "/"))
            base_theme = str(self.theme_tokens.get("base_ttk_theme", "forest-light"))
            style.theme_use(base_theme)
        except Exception as exc:
            messagebox.showwarning(
                "Тема Forest недоступна",
                f"Не удалось загрузить Forest theme. Используется стандартная тема.\n{exc}",
            )

    def _not_implemented(self) -> None:
        messagebox.showinfo("В разработке", "Функция будет реализована на следующем шаге.")


def main() -> None:
    app = KanbanTkApp()
    app.mainloop()


if __name__ == "__main__":
    main()
