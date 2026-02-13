"""Tkinter desktop UI for Project Kanban."""
from __future__ import annotations

import json
import os
import getpass
from dataclasses import dataclass
from datetime import date, datetime
from tkinter import BOTH, END, LEFT, RIGHT, TOP, VERTICAL, StringVar, Tk, Toplevel
from tkinter import font as tkfont
from tkinter import messagebox, simpledialog, ttk
from typing import Any

from ui_tk.api_client import ApiClient, ApiClientError

try:
    from tkcalendar import Calendar
except Exception:
    Calendar = None


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

        self._build_menu()
        self._build_ribbon()
        self._build_zones()
        self._show_zone("dashboard")
        self._load_dashboard_data()

    def _build_menu(self) -> None:
        self.menu_bar = ttk.Frame(self, padding=(8, 4))
        self.menu_bar.pack(side=TOP, fill="x")
        self._menu_actions: dict[str, Any] = {
            "Карманы": self._open_pockets_window,
            "Проекты": self._open_projects_window,
            "Задачи": self._open_tasks_window,
            "Пользователи": self._not_implemented,
            "Статусы": self._not_implemented,
            "База данных": self._not_implemented,
            "Экспорт": self._not_implemented,
            "Информация о теме": self._show_theme_info,
            "Руководство пользователя": self._not_implemented,
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
        )
        self.top_tree = ttk.Treeview(top, columns=top_cols, show="headings")
        for col in top_cols:
            self.top_tree.heading(col, text=TOP_COLUMN_TITLES.get(col, col))
            self.top_tree.column(col, width=120, anchor="w")
        self.top_tree.column("pocket_id", anchor="center")
        self.top_tree.column("project_id", anchor="center")
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
        return w

    def _can_manage_pockets(self) -> bool:
        if not self.session_user:
            return False
        role = str(self.session_user.get("role", "executor"))
        return role in {"admin", "head"}

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
        self._mk_button(actions, "Создать", self._open_pocket_form_create).pack(side=LEFT, padx=2)
        self._mk_button(actions, "Изменить", self._open_pocket_form_edit).pack(side=LEFT, padx=2)
        self._mk_button(actions, "В архив", self._archive_selected_pocket).pack(side=LEFT, padx=2)
        ttk.Label(actions, text="Удаление не предусмотрено, используйте 'В архив'.", style="Surface.TLabel").pack(
            side=LEFT, padx=14
        )

        if not self._can_manage_pockets():
            for child in actions.winfo_children():
                if isinstance(child, ttk.Button) and child.cget("text") in {"Создать", "Изменить", "В архив"}:
                    child.state(["disabled"])

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
        if not self._can_manage_pockets():
            messagebox.showwarning("Недостаточно прав", "Доступно только ролям admin/head.", parent=self.pocket_window)
            return

        if not self.pocket_users_by_id:
            try:
                self.pocket_users_by_id = {int(u["id"]): u for u in self.api.list_users()}
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
            messagebox.showwarning("Недостаточно прав", "Доступно только ролям admin/head.", parent=self.pocket_window)
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
            messagebox.showwarning("Недостаточно прав", "Доступно только ролям admin/head.", parent=self.project_window)
            return
        try:
            users = {int(u["id"]): u for u in self.api.list_users()}
            pockets = self.api.list_pockets()
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
            messagebox.showwarning("Недостаточно прав", "Доступно только ролям admin/head.", parent=self.project_window)
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
            users = {int(u["id"]): u for u in self.api.list_users()}
            pockets = {int(p["id"]): p for p in self.api.list_pockets()}
            projects = self.api.list_projects()
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
        ttk.Entry(basic, textvariable=customer_var).grid(row=4, column=1, sticky="ew", pady=4)
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
                project.get("project_code", "") or "",
                project.get("date_start") or "",
                project.get("date_end") or "",
                project.get("status") or "",
                owner,
                owner_it,
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
            ),
            rows_for_width,
            min_width=90,
            max_width_overrides={"project_name": 320, "owner": 220, "owner_it": 220},
        )

    def _on_top_select(self, _: object) -> None:
        selected = self.top_tree.selection()
        self.selected_project_id = int(selected[0]) if selected else None
        self._apply_filters()

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
        self._close_pockets_window()
        self._close_projects_window()
        self._close_tasks_window()
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
        # Keep dropdown list popups aligned with light Forest defaults.
        self.option_add("*TCombobox*Listbox.background", "#ffffff")
        self.option_add("*TCombobox*Listbox.foreground", "#1f2328")
        self.option_add("*TCombobox*Listbox.selectBackground", "#217346")
        self.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")

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
