# Схема БД (логическая, Sprint 2)

Документ описывает целевую логическую схему данных Sprint 2.
Опирается на `md_docs/architecture.md`, `md_docs/tasks_rules.md`, `md_docs/wip_rules.md`.

---

## 1. Основные таблицы

### 1.1 users (Пользователь)

Поля:

- `id` — идентификатор
- `login` — Windows-логин (уникальный)
- `full_name` — ФИО
- `role` — роль пользователя (`admin` / `head` / `teamlead` / `curator` / `executor`)
- `status_id` — статус пользователя (FK -> `statuses.id`, `entity_type = user`)

### 1.2 pockets (Карман)

Поля:

- `id` — идентификатор
- `name` — наименование
- `date_start` — дата начала
- `date_end` — дата окончания
- `status_id` — статус кармана (FK -> `statuses.id`, `entity_type = pocket`)
- `owner_user_id` — ответственный (FK -> `users.id`)
- `department` — подразделение

### 1.3 projects (Проект)

Поля:

- `id` — идентификатор
- `name` — наименование
- `pocket_id` — карман (FK -> `pockets.id`)
- `status_id` — статус проекта (FK -> `statuses.id`, `entity_type = project`)
- `date_start` — дата начала
- `date_end` — дата окончания
- `curator_business_user_id` — куратор бизнес (FK -> `users.id`)
- `curator_it_user_id` — куратор ИТ (FK -> `users.id`)

### 1.4 tasks (Задача)

Поля:

- `id` — идентификатор
- `description` — описание
- `project_id` — проект (FK -> `projects.id`)
- `status_id` — статус задачи (FK -> `statuses.id`, `entity_type = task`)
- `date_created` — дата создания
- `date_start_work` — дата начала работы
- `date_done` — дата завершения
- `executor_user_id` — исполнитель (FK -> `users.id`)
- `customer` — заказчик
- `code_link` — ссылка на код

### 1.5 task_pauses (Приостановки задач)

Поля:

- `id` — идентификатор
- `task_id` — задача (FK -> `tasks.id`)
- `date_start` — дата начала паузы
- `date_end` — дата окончания паузы

### 1.6 action_log (Журнал действий)

Поля:

- `id` — идентификатор
- `timestamp` — дата/время события
- `user_id` — пользователь (FK -> `users.id`)
- `entity_type` — тип сущности (`pocket` / `project` / `task` / `user`)
- `entity_id` — идентификатор сущности
- `action_type` — тип действия
- `old_value` — предыдущее значение (nullable)
- `new_value` — новое значение (nullable)
- `comment` — комментарий (nullable)

Допустимые `action_type`:

- `create`
- `update_status`
- `assign`
- `pause_start`
- `pause_end`
- `close`
- `edit`

---

## 2. Справочники

### 2.1 statuses (Единый справочник статусов)

Поля:

- `id` — идентификатор
- `name` — наименование статуса
- `entity_type` — тип сущности (`pocket` / `project` / `task` / `user`)
- `sort_order` — порядок отображения (опционально)
- `is_active` — признак активности статуса (опционально)

Нормативные наборы:

- `entity_type = pocket`: `Запущен`, `Завершен`
- `entity_type = project`: `Активен`, `Завершен`
- `entity_type = task`: `Создана`, `В работе`, `Приостановлена`, `Завершена`
- `entity_type = user`: `Активен`, `Неактивен`

---

## 3. Связи

- `users (1) -> pockets (many)` через `pockets.owner_user_id`
- `users (1) -> projects (many)` через `projects.curator_business_user_id`, `projects.curator_it_user_id`
- `users (1) -> tasks (many)` через `tasks.executor_user_id`
- `users (1) -> action_log (many)` через `action_log.user_id`
- `pockets (1) -> projects (many)` через `projects.pocket_id`
- `projects (1) -> tasks (many)` через `tasks.project_id`
- `tasks (1) -> task_pauses (many)` через `task_pauses.task_id`
- `statuses (1) -> users/pockets/projects/tasks (many)` через соответствующие `status_id`

---

## 4. Ограничения и правила

- Все даты ведутся в календарных днях.
- В задаче на старте один исполнитель.
- Жизненный цикл задач и допустимые переходы определяются `md_docs/architecture.md` и `md_docs/tasks_rules.md`.
- Схема не включает автоматическую оптимизацию и рекомендации.

---

## 5. Устаревшие элементы

Таблицы `pocket_statuses`, `project_statuses`, `task_statuses` считаются устаревшими и не являются нормативными для Sprint 2.
