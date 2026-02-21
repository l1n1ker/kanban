from __future__ import annotations

import json

import ui_tk.main as ui_main


def _new_app() -> ui_main.KanbanTkApp:
    return ui_main.KanbanTkApp.__new__(ui_main.KanbanTkApp)


def test_theme_json_load_success() -> None:
    app = _new_app()
    tokens = app._load_theme_tokens("forest-light")
    assert tokens["id"] == "forest-light"
    assert "colors" in tokens and "roles" in tokens and "icons" in tokens


def test_theme_json_missing_key_fallback(tmp_path, monkeypatch) -> None:
    app = _new_app()
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps({"id": "broken"}), encoding="utf-8")
    monkeypatch.setattr(ui_main, "_theme_file", lambda _theme_id: str(broken))
    tokens = app._load_theme_tokens_with_fallback("broken")
    assert tokens["id"] == "forest-light"


def test_role_colors_from_json_applied() -> None:
    app = _new_app()
    app.theme_tokens = {
        "roles": {
            "admin": "#111111",
            "head": "#222222",
            "teamlead": "#333333",
            "curator": "#444444",
            "executor": "#555555",
        }
    }
    roles = app._role_palette_for_theme("forest-light")
    assert roles["admin"] == "#111111"
    assert roles["executor"] == "#555555"


def test_icon_palette_switch_by_theme() -> None:
    app = _new_app()
    app.theme_tokens = {"icons": {"palette": "dark"}}
    paths = app._resolve_kanban_icon_paths("forest-dark")
    assert paths
    assert all("\\dark\\" in p.lower() for p in paths.values())


def test_theme_switch_persists_to_ui_config(tmp_path, monkeypatch) -> None:
    app = _new_app()
    app.theme_name = "forest-light"
    app.theme_tokens = app._load_theme_tokens("forest-light")
    app.role_colors = app._role_palette_for_theme("forest-light")
    app._rebuild_ui = lambda: None

    class DummyVar:
        def __init__(self) -> None:
            self.value = ""

        def set(self, value: str) -> None:
            self.value = value

    app.theme_var = DummyVar()
    cfg = tmp_path / "ui_config.json"
    monkeypatch.setattr(ui_main, "_ui_config_file", lambda: str(cfg))
    app._set_theme("forest-dark")
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert data["theme"] == "forest-dark"
