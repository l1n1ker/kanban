# PocketFlow Kanban

PocketFlow Kanban - локальная Kanban-система для управления работой по модели
`Карман -> Проект -> Задача`.

Текущая ветка разработки и публикации: `master`.
Актуальное состояние проекта фиксируется только по последнему `master`.

## Состав

- `backend/` - FastAPI backend и бизнес-логика
- `ui_tk/` - desktop UI на Tkinter
- `sql/` - скрипты очистки, сидирования и проверки demo-данных
- `md_docs/` - нормативные документы проекта
- `tests/` - автоматические тесты

## Источник истины

Нормативная документация хранится в `md_docs/`.

Ключевые документы:

- `md_docs/README.md`
- `md_docs/architecture.md`
- `md_docs/db_schema.md`
- `md_docs/tasks_rules.md`
- `md_docs/wip_rules.md`
- `md_docs/workflow.md`
- `md_docs/ui_structure.md`

## Запуск

### Вариант 1. Один bat-файл

Из `cmd`:

```bat
run_server_and_app.bat
```

Скрипт:

1. запускает backend на `127.0.0.1:8000`
2. затем запускает Tkinter-приложение

### Вариант 2. Вручную

Backend:

```bat
.venv\Scripts\python.exe -m uvicorn backend.http.app:app --host 127.0.0.1 --port 8000
```

UI:

```bat
.venv\Scripts\python.exe -m ui_tk.main
```

## Demo-данные

В проекте подготовлены осмысленные demo-данные на русском языке:

- карманы: `Работа в огороде`, `Постройка дома`, `Выращивание скота`
- пользователи с ФИО
- проекты, задачи, паузы и журнал действий

Применение сидов:

```bat
powershell -ExecutionPolicy Bypass -File sql\99_apply_seed.ps1
```

## Тесты

```bat
.venv\Scripts\python.exe -m pytest -q
```

## Стек

- Python
- FastAPI
- SQLite
- Tkinter
- Pytest

