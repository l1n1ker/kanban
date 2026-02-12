# Схема БД (логическая)

Документ описывает логическую схему данных Sprint 1.
Опирается строго на `md_docs/architecture.md`.
SQL и оптимизации не используются.

---

## Таблицы (основные сущности)

### 1. users (Пользователь)
Поля:
- `id` — идентификатор
- `login` — Windows-логин (уникальный)
- `full_name` — ФИО
- `role` — роль пользователя (строка из фиксированного набора)
- `is_active` — активен/неактивен (логическое поле)

Фиксированный набор ролей (без справочника):
- `admin`
- `head`
- `teamlead`
- `curator`
- `executor`

### 2. pockets (Карман)
Поля:
- `id` — идентификатор
- `name` — наименование
- `date_start` — дата_начала (дата, календарные дни)
- `date_end` — дата_окончания (дата, календарные дни)
- `status` — статус (ссылка на справочник `pocket_statuses`)
- `owner_user_id` — ответственный (ссылка на `users.id`)
- `department` — подразделение (строка)

### 3. projects (Проект)
Поля:
- `id` — идентификатор
- `name` — наименование
- `pocket_id` — id_кармана (ссылка на `pockets.id`)
- `status` — статус (ссылка на справочник `project_statuses`)
- `date_start` — дата_начала (дата, календарные дни)
- `date_end` — дата_окончания (дата, календарные дни)
- `curator_business_user_id` — куратор_бизнес (ссылка на `users.id`)
- `curator_it_user_id` — куратор_ит (ссылка на `users.id`)

### 4. tasks (Задача)
Поля:
- `id` — идентификатор
- `description` — описание (текст)
- `project_id` — id_проекта (ссылка на `projects.id`)
- `status` — статус (ссылка на справочник `task_statuses`)
- `date_created` — дата_создания (дата, календарные дни)
- `date_start_work` — дата_начала_работы (дата, календарные дни)
- `date_done` — дата_завершения (дата, календарные дни)
- `executor_user_id` — исполнитель (ссылка на `users.id`; на старте один исполнитель)
- `customer` — заказчик (строка)
- `code_link` — ссылка_на_код (строка/URL)

### 5. task_pauses (Приостановки задач)
Поля:
- `id` — идентификатор
- `task_id` — id_задачи (ссылка на `tasks.id`)
- `date_start` — дата_начала (дата, календарные дни)
- `date_end` — дата_окончания (дата, календарные дни)

### 6. action_log (Журнал действий)
Поля:
- `id` — идентификатор
- `timestamp` — дата и время события (datetime)
- `user_id` — пользователь (ссылка на `users.id`)
- `entity_type` — тип сущности (pocket / project / task / user)
- `entity_id` — идентификатор сущности
- `action_type` — тип действия
  - `create`
  - `update_status`
  - `assign`
  - `pause_start`
  - `pause_end`
  - `close`
  - `edit`
- `old_value` — предыдущее значение (текст, nullable)
- `new_value` — новое значение (текст, nullable)
- `comment` — комментарий пользователя (опционально)

---

## Таблицы (справочники)

### A. pocket_statuses
Справочник статусов кармана:
- `Запущен`
- `Завершён`

### B. project_statuses
Справочник статусов проекта:
- `Активен`
- `Завершён`

### C. task_statuses
Справочник статусов задачи:
- `Создана`
- `В работе`
- `Приостановлена`
- `Завершена`

---

## Связи между таблицами

- `users (1) -> pockets (many)`
  - `pockets.owner_user_id` ссылается на `users.id`.
- `users (1) -> projects (many)`
  - `projects.curator_business_user_id` ссылается на `users.id`.
  - `projects.curator_it_user_id` ссылается на `users.id`.
- `users (1) -> tasks (many)`
  - `tasks.executor_user_id` ссылается на `users.id`.
- `users (1) -> action_log (many)`
  - `action_log.user_id` ссылается на `users.id`.
- `pockets (1) -> projects (many)`
  - `projects.pocket_id` ссылается на `pockets.id`.
- `projects (1) -> tasks (many)`
  - `tasks.project_id` ссылается на `projects.id`.
- `tasks (1) -> task_pauses (many)`
  - `task_pauses.task_id` ссылается на `tasks.id`.

---

## Ограничения и правила (без автоматизации)

- Все даты учитываются в календарных днях.
- В задаче всегда один исполнитель на старте.
- Схема не предусматривает автоматические механизмы, рекомендации или оптимизации.
