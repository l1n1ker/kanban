PRAGMA foreign_keys = ON;
BEGIN TRANSACTION;

INSERT INTO pockets (id, name, date_start, date_end, status, status_id, owner_user_id, department) VALUES
(101, 'P1', '2026-02-01', NULL, 'Запущен', (SELECT id FROM statuses WHERE entity_type='pocket' AND name='Запущен' LIMIT 1), 3, 'Delivery'),
(102, 'P2', '2026-02-01', NULL, 'Запущен', (SELECT id FROM statuses WHERE entity_type='pocket' AND name='Запущен' LIMIT 1), 4, 'Delivery'),
(103, 'P3', '2026-02-01', NULL, 'Запущен', (SELECT id FROM statuses WHERE entity_type='pocket' AND name='Запущен' LIMIT 1), 5, 'Delivery'),
(104, 'PH', '2026-02-01', NULL, 'Запущен', (SELECT id FROM statuses WHERE entity_type='pocket' AND name='Запущен' LIMIT 1), 2, 'Delivery');

INSERT INTO projects (id, name, project_code, pocket_id, status, status_id, date_start, date_end, curator_business_user_id, curator_it_user_id) VALUES
(201, 'PR1A', 'PR1A-CODE', 101, 'Активен', (SELECT id FROM statuses WHERE entity_type='project' AND name='Активен' LIMIT 1), '2026-02-01', NULL, 3, 3),
(202, 'PR1B', 'PR1B-CODE', 101, 'Активен', (SELECT id FROM statuses WHERE entity_type='project' AND name='Активен' LIMIT 1), '2026-02-01', NULL, 3, 3),
(203, 'PR2A', 'PR2A-CODE', 102, 'Активен', (SELECT id FROM statuses WHERE entity_type='project' AND name='Активен' LIMIT 1), '2026-02-01', NULL, 4, 4),
(204, 'PR3A', 'PR3A-CODE', 103, 'Активен', (SELECT id FROM statuses WHERE entity_type='project' AND name='Активен' LIMIT 1), '2026-02-01', NULL, 5, 5),
(205, 'PRH1', 'PRH1-CODE', 104, 'Активен', (SELECT id FROM statuses WHERE entity_type='project' AND name='Активен' LIMIT 1), '2026-02-01', NULL, 2, 2);

COMMIT;
