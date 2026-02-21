PRAGMA foreign_keys = ON;
BEGIN TRANSACTION;

INSERT INTO tasks (id, description, project_id, status, status_id, date_created, date_start_work, date_done, executor_user_id, customer, code_link) VALUES
(301, 'TQ_1 queue unassigned', 201, 'Создана', (SELECT id FROM statuses WHERE entity_type='task' AND name='Создана' LIMIT 1), '2026-02-10', NULL, NULL, NULL, 'Biz', NULL),
(302, 'TQ_2 queue unassigned', 203, 'Создана', (SELECT id FROM statuses WHERE entity_type='task' AND name='Создана' LIMIT 1), '2026-02-10', NULL, NULL, NULL, 'Biz', NULL),
(303, 'TC_1 created assigned', 201, 'Создана', (SELECT id FROM statuses WHERE entity_type='task' AND name='Создана' LIMIT 1), '2026-02-10', NULL, NULL, 6, 'Biz', NULL),
(304, 'TC_2 created assigned', 204, 'Создана', (SELECT id FROM statuses WHERE entity_type='task' AND name='Создана' LIMIT 1), '2026-02-10', NULL, NULL, 7, 'Biz', NULL),
(305, 'TW_1 in progress', 201, 'В работе', (SELECT id FROM statuses WHERE entity_type='task' AND name='В работе' LIMIT 1), '2026-02-09', '2026-02-10', NULL, 8, 'Biz', NULL),
(306, 'TW_2 in progress', 203, 'В работе', (SELECT id FROM statuses WHERE entity_type='task' AND name='В работе' LIMIT 1), '2026-02-09', '2026-02-10', NULL, 9, 'Biz', NULL),
(307, 'TP_1 paused', 202, 'Приостановлена', (SELECT id FROM statuses WHERE entity_type='task' AND name='Приостановлена' LIMIT 1), '2026-02-08', '2026-02-09', NULL, 10, 'Biz', NULL),
(308, 'TP_2 paused', 205, 'Приостановлена', (SELECT id FROM statuses WHERE entity_type='task' AND name='Приостановлена' LIMIT 1), '2026-02-08', '2026-02-09', NULL, 11, 'Biz', NULL),
(309, 'TD_1 done', 201, 'Завершена', (SELECT id FROM statuses WHERE entity_type='task' AND name='Завершена' LIMIT 1), '2026-02-01', '2026-02-02', '2026-02-04', 12, 'Biz', NULL),
(310, 'TD_2 done', 203, 'Завершена', (SELECT id FROM statuses WHERE entity_type='task' AND name='Завершена' LIMIT 1), '2026-02-01', '2026-02-02', '2026-02-04', 13, 'Biz', NULL);

COMMIT;
