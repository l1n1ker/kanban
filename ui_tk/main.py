"""Tkinter desktop UI for Project Kanban."""
from __future__ import annotations

import json
import os
import getpass
from dataclasses import dataclass
from datetime import date
from tkinter import BOTH, END, LEFT, RIGHT, TOP, VERTICAL, StringVar, Tk, Toplevel
from tkinter import font as tkfont
from tkinter import messagebox, simpledialog, ttk
from typing import Any

from ui_tk.api_client import ApiClient, ApiClientError


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
    "action": "Действие",
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
THEME_CONFIGS: dict[str, dict[str, str]] = {
    "forest-light": {"admin": "#b42318", "head": "#b54708", "teamlead": "#175cd3", "curator": "#067647", "executor": "#57606a"},
    "forest-dark": {"admin": "#ff8a80", "head": "#f9d37a", "teamlead": "#8ab4ff", "curator": "#8dd9a5", "executor": "#c2c9d2"},
}


def _app_dir() -> str:
    base = os.getenv("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "project-kanban")
    os.makedirs(path, exist_ok=True)
    return path


def _preset_file() -> str:
    return os.path.join(_app_dir(), "filter_presets.json")


def _ui_config_file() -> str:
    return os.path.join(_app_dir(), "ui_config.json")


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


class KanbanTkApp(Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Project Kanban - Tkinter UI")
        self.geometry("1400x860")
        self.system_login = (os.getenv("PROJECT_KANBAN_LOGIN") or os.getenv("USERNAME") or getpass.getuser()).strip()
        self.api = ApiClient(actor_user_login=self.system_login)
        self.session_user: dict[str, Any] | None = None
        self.session_var = StringVar(value=f"Сессия: login={self.system_login}")
        self.theme_name = self._load_theme_name()
        self.theme_var = StringVar(value=self.theme_name)
        self.role_colors = self._role_palette_for_theme(self.theme_name)
        self._setup_forest_theme()
        self._apply_theme_settings()

        self.users_by_id: dict[int, dict[str, Any]] = {}
        self.pockets_by_id: dict[int, dict[str, Any]] = {}
        self.projects_by_id: dict[int, dict[str, Any]] = {}
        self.tasks_all: list[dict[str, Any]] = []
        self.selected_project_id: int | None = None
        self.current_zone = "dashboard"

        self.filter_visible = False
        self.filter_rows: list[FilterRow] = []
        self.presets = self._load_presets()
        self.filter_summary_var = StringVar(value="Фильтр: пуст")
        self._filter_summary_full_text = "Фильтр пуст"
        self._filter_tooltip: Toplevel | None = None

        self._build_menu()
        self._build_ribbon()
        self._build_zones()
        self._show_zone("dashboard")
        self._load_dashboard_data()

    def _build_menu(self) -> None:
        self.menu_bar = ttk.Frame(self, padding=(8, 4))
        self.menu_bar.pack(side=TOP, fill="x")
        self._menu_actions: dict[str, Any] = {
            "Новый карман": self._not_implemented,
            "Новый проект": self._not_implemented,
            "Новая задача": self._not_implemented,
            "Пользователи": self._not_implemented,
            "Статусы": self._not_implemented,
            "База данных": self._not_implemented,
            "Экспорт": self._not_implemented,
            "Информация о теме": self._show_theme_info,
            "Руководство пользователя": self._not_implemented,
            "О программе": self._show_about,
        }
        self._menu_vars: list[StringVar] = []
        self._mk_vendor_option_menu("Главная", ["Новый карман", "Новый проект", "Новая задача"])
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
        self._mk_button(self.ribbon, "☀", self._theme_in_development, width=3).pack(side=RIGHT, padx=2)
        self._mk_button(self.ribbon, "🌙", self._theme_in_development, width=3).pack(side=RIGHT, padx=2)
        self.session_label = ttk.Label(
            self.ribbon,
            textvariable=self.session_var,
            cursor="hand2",
            style="Session.TLabel",
            padding=(8, 2),
        )
        self.session_label.pack(side=RIGHT, padx=4)
        self.session_label.bind("<Button-1>", self._on_session_click)

    def _build_zones(self) -> None:
        self.zones: dict[str, ttk.Frame] = {}
        container = ttk.Frame(self)
        container.pack(fill=BOTH, expand=True)

        dashboard = ttk.Frame(container)
        self._build_dashboard(dashboard)
        self.zones["dashboard"] = dashboard

        for name, caption in (
            ("kanban", "Kanban (в разработке)"),
            ("timeline", "Timeline (в разработке)"),
            ("analytics", "Аналитика (в разработке)"),
        ):
            frame = ttk.Frame(container)
            ttk.Label(frame, text=caption).pack(pady=30)
            self.zones[name] = frame

    def _build_dashboard(self, parent: ttk.Frame) -> None:
        toolbar = ttk.Frame(parent, padding=(8, 8))
        toolbar.pack(fill="x")
        self._mk_button(toolbar, "Обновить", self._load_dashboard_data).pack(side=LEFT)

        vertical = ttk.Panedwindow(parent, orient=VERTICAL)
        vertical.pack(fill=BOTH, expand=True, padx=8, pady=8)

        top = ttk.Frame(vertical)
        bottom = ttk.Frame(vertical)
        vertical.add(top, weight=1)
        vertical.add(bottom, weight=1)

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
            "action",
        )
        self.top_tree = ttk.Treeview(top, columns=top_cols, show="headings")
        for col in top_cols:
            self.top_tree.heading(col, text=TOP_COLUMN_TITLES.get(col, col))
            self.top_tree.column(col, width=120, anchor="w")
        self.top_tree.column("pocket_id", anchor="center")
        self.top_tree.column("project_id", anchor="center")
        self.top_tree.column("action", width=110, anchor="center")
        self.top_tree.pack(fill=BOTH, expand=True)
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
        self.bottom_tree.pack(fill=BOTH, expand=True)

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

    def _show_zone(self, name: str) -> None:
        self.current_zone = name
        for frame in self.zones.values():
            frame.pack_forget()
        self.zones[name].pack(fill=BOTH, expand=True)

    def _toggle_filter_panel(self) -> None:
        self.filter_visible = not self.filter_visible
        if self.filter_visible:
            self.filter_panel.pack(fill="x", before=self.bottom_controls)
        else:
            self.filter_panel.pack_forget()

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
        self._fill_top_table(projects)
        self._apply_filters()

    def _on_session_click(self, _: object) -> None:
        if not self.session_user:
            messagebox.showinfo("Сеанс", "Данные сессии еще не загружены.")
            return
        self._open_session_user_card()

    def _open_session_user_card(self) -> None:
        if not self.session_user:
            return
        w = Toplevel(self)
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

    def _fill_top_table(self, projects: list[dict[str, Any]]) -> None:
        self.top_tree.delete(*self.top_tree.get_children())
        rows_for_width: list[tuple[Any, ...]] = []
        for project in projects:
            pocket = self.pockets_by_id.get(int(project["pocket_id"]), {})
            owner = self.users_by_id.get(int(pocket.get("owner_user_id", 0)), {}).get("full_name", "")
            owner_it = self.users_by_id.get(int(project["curator_it_user_id"]), {}).get("full_name", "")
            values = (
                pocket.get("id", ""),
                pocket.get("name", ""),
                project["id"],
                project["name"],
                "",
                project.get("date_start") or "",
                project.get("date_end") or "",
                project.get("status") or "",
                owner,
                owner_it,
                "Открыть",
            )
            rows_for_width.append(values)
            self.top_tree.insert("", END, iid=str(project["id"]), values=values)
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
                "action",
            ),
            rows_for_width,
            min_width=90,
            max_width_overrides={"project_name": 320, "owner": 220, "owner_it": 220, "action": 120},
        )

    def _on_top_select(self, _: object) -> None:
        selected = self.top_tree.selection()
        self.selected_project_id = int(selected[0]) if selected else None
        self._apply_filters()

    def _on_top_double_click(self, event: object) -> None:
        region = self.top_tree.identify_region(getattr(event, "x"), getattr(event, "y"))
        col = self.top_tree.identify_column(getattr(event, "x"))
        if region == "cell" and col == "#11":
            selected = self.top_tree.selection()
            if not selected:
                return
            project = self.projects_by_id.get(int(selected[0]))
            if project:
                self._open_project_popup(project)

    def _open_project_popup(self, project: dict[str, Any]) -> None:
        w = Toplevel(self)
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
        for row in self.filter_rows:
            row.frame.destroy()
        self.filter_rows.clear()
        self._apply_filters()

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
        rows = [self._build_task_view(t) for t in self.tasks_all]
        if self.selected_project_id is not None:
            rows = [r for r in rows if int(r["project_id"]) == self.selected_project_id]

        for idx, cond in enumerate(self.filter_rows):
            field = cond.field_var.get()
            op = cond.op_var.get()
            raw = cond.value_var.get()
            if not field or not op:
                continue
            filtered = [r for r in rows if self._match_condition(r.get(field), op, raw)]
            if idx == 0:
                rows = filtered
            elif cond.logic_var.get() == "AND":
                rows = filtered
            else:
                ids = {int(r["id"]) for r in rows}
                for item in filtered:
                    if int(item["id"]) not in ids:
                        rows.append(item)

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
        self._refresh_filter_indicator()
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

    def _serialize_filters(self) -> list[dict[str, str]]:
        payload: list[dict[str, str]] = []
        for idx, row in enumerate(self.filter_rows):
            payload.append(
                {
                    "logic": row.logic_var.get() if idx > 0 else "AND",
                    "field": row.field_var.get(),
                    "op": row.op_var.get(),
                    "value": row.value_var.get(),
                }
            )
        return payload

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
        self._refresh_filter_indicator()

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

    def _show_about(self) -> None:
        messagebox.showinfo("О программе", "Project Kanban Tkinter UI (MVP)")

    def _show_theme_info(self) -> None:
        messagebox.showinfo(
            "Тема интерфейса",
            (
                f"Активная тема: {self.theme_name}\n"
                f"Файл темы: {_forest_theme_file(self.theme_name)}\n"
                "Тема сохраняется в локальном ui_config.json."
            ),
        )

    def _on_theme_selected(self) -> None:
        self._theme_in_development()

    def _set_theme(self, theme_name: str) -> None:
        _ = theme_name
        self._theme_in_development()

    def _theme_in_development(self) -> None:
        messagebox.showinfo("В разработке", "Переключение темы временно отключено.")

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
        if self.theme_name == "forest-dark":
            menu_widget.configure(
                tearoff=False,
                bg="#313131",
                fg="#ffffff",
                activebackground="#217346",
                activeforeground="#ffffff",
            )
        else:
            menu_widget.configure(
                tearoff=False,
                bg="#ffffff",
                fg="#1f2328",
                activebackground="#217346",
                activeforeground="#ffffff",
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
        parts: list[str] = []
        for idx, cond in enumerate(self.filter_rows):
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
        full_text = self._format_filter_text()
        self._filter_summary_full_text = full_text
        if full_text == "Фильтр пуст":
            self.filter_summary_var.set(full_text)
            return
        short_text = full_text if len(full_text) <= 100 else f"{full_text[:100].rstrip()}..."
        self.filter_summary_var.set(short_text)

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

    def _rebuild_ui(self) -> None:
        self._hide_filter_tooltip()
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
        # Theme switch is temporarily disabled; keep UI on light forest.
        return "forest-light"

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

    def _role_palette_for_theme(self, theme_name: str) -> dict[str, str]:
        return dict(THEME_CONFIGS.get(theme_name, THEME_CONFIGS["forest-light"]))

    def _apply_theme_settings(self) -> None:
        style = ttk.Style(self)
        style.configure("Session.TLabel", foreground=self.role_colors.get("executor", "#57606a"))

    def _setup_forest_theme(self) -> None:
        style = ttk.Style(self)
        try:
            self.tk.call("source", _forest_theme_file("forest-light").replace("\\", "/"))
            self.tk.call("source", _forest_theme_file("forest-dark").replace("\\", "/"))
            style.theme_use(self.theme_name)
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
