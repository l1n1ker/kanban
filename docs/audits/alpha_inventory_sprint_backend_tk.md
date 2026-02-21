# Alpha Inventory & Compliance Audit (Sprint Backend + Tkinter)

Дата: 2026-02-21  
Ветка: `feature/ui-v2`  
Базовый коммит: `f2f24ce`  
Принятый baseline истины: `md_docs/*` (strict)

## 1. Freeze snapshot

### 1.1 Состав модулей
- `backend/`: API, сервисы, репозитории, RBAC, DB init/migrations.
- `ui_tk/`: desktop-клиент Tkinter, API client, темы/иконки.
- `tests/`: API, RBAC, Kanban/Timeline UI smoke, theme/config проверки.
- `sql/`: seed/backup/verify скрипты.
- `md_docs/`: архитектура, БД, workflow, UI, WIP и матрицы.

### 1.2 Критичные артефакты истины
- `md_docs/architecture.md`
- `md_docs/db_schema.md`
- `md_docs/workflow.md`
- `md_docs/tasks_rules.md`
- `md_docs/wip_rules.md`
- `md_docs/ui_structure.md`

## 2. Нормативная матрица “Норма -> Код -> Тест”

| Направление | Норма | Код | Тест | Статус |
|---|---|---|---|---|
| Status truth-model | `status_id` как канон | `backend/services.py`, `backend/repositories.py`, `backend/db.py` | `tests/test_truth_invariants.py` | Fix now |
| RBAC task actions | управление статусом задачи только `curator+` | `backend/rbac.py`, `backend/services.py`, `ui_tk/main.py` | `tests/test_rbac.py`, `tests/test_tasks.py`, `tests/test_kanban_flow.py` | Fix now |
| Task lifecycle | только разрешенные переходы | `backend/services.py` | `tests/test_tasks.py` | Pass |
| WIP semantics | только `В работе`, без автопринятия решений | `backend/services.py` | существующие API/UI тесты + инварианты | Pass |
| Action log semantics | append-only, обязательные события | `backend/logging.py`, `backend/services.py` | `tests/test_truth_invariants.py` | Fix now |
| UI role visibility/editability | роли и read-only в UI по нормативу | `ui_tk/main.py` | `tests/test_ui_kanban_dashboard.py` | Fix now |

## 3. Что исправлено в спринте

### 3.1 Backend
- RBAC: `tasks.claim` ограничен до `curator+` (`backend/rbac.py`).
- Status canonicalization:
  - фильтрация list-операций поддерживает `status_id` приоритетно (`backend/repositories.py`, `backend/services.py`);
  - task lifecycle и WIP используют каноническое определение статуса через `status_id` (`backend/services.py`).
- DB hardening:
  - добавлена синхронизация legacy `status` с каноническим `status_id` и self-check обязательных системных статусов (`backend/db.py`).
- API hardening:
  - startup переведен с deprecated `on_event` на lifespan (`backend/http/app.py`).
- Logging hardening:
  - UTC timestamp переведен на timezone-aware (`backend/logging.py`).

### 3.2 Tkinter
- UI role gate для управления карманами выровнен (`teamlead` включен) (`ui_tk/main.py`).
- Убрано действие claim из доступных Kanban-кнопок для read-only роли `executor`; в UI-гайде убрано описание claim как действия executor (`ui_tk/main.py`).

### 3.3 Тестовый контур
- Обновлены RBAC/lifecycle сценарии под strict truth:
  - `tests/test_tasks.py`
  - `tests/test_kanban_flow.py`
  - `tests/test_rbac.py`
  - `tests/test_ui_kanban_dashboard.py`
- Добавлены инвариантные тесты truth-model и action_log:
  - `tests/test_truth_invariants.py`

### 3.4 Документация
- Добавлен платформенно-независимый UI-контракт в `md_docs/ui_structure.md`.
- Обновлена ссылка на UI-контракт в `md_docs/README.md`.
- Обновлена матрица RBAC/Kanban под новую норму claim (`md_docs/test_matrix_rbac_kanban.md`).

## 4. Compat bridge (осознанно оставлено)

1. В схеме БД сохраняются legacy текстовые поля `status` для обратной совместимости.
2. В API поле `status` оставлено как совместимое представление (derived from `status_id`), пока не завершен полный отказ от legacy-полей.

## 5. Risk register (P0/P1/P2)

### P0
- Расхождение RBAC между backend и UI при дальнейших изменениях ролей.
- Риск повторного рассогласования `status`/`status_id` при ручных SQL-операциях.

### P1
- Поддержка compat bridge (`status` + `status_id`) усложняет сопровождение.
- Возможны дополнительные edge-cases в старых данных, где legacy статус неконсистентен.

### P2
- Техдолг по окончательному удалению legacy status tables/polей после окна совместимости.

## 6. Quality gates

- `pytest -q`: PASS.
- P0 расхождения по RBAC/task-status truth закрыты в коде и тестах.
- Deprecated warnings по startup/UTC закрыты.

## 7. Итоговый compliance report

### Исправлено
- Truth-model статусов в core-операциях.
- RBAC по task status actions приведен к `curator+`.
- UI role gates выровнены для `teamlead` по карманам.
- Устранены deprecation-точки FastAPI startup и UTC timestamp.

### В compat bridge
- Legacy `status` текстовые колонки остаются до отдельного migration-cleanup.

### Отложено
- Полное удаление legacy status tables/columns и cleanup миграций.
- Формализация отдельного ADR по срокам отключения compat bridge.
