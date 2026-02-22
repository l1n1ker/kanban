PRAGMA foreign_keys = ON;
BEGIN TRANSACTION;

INSERT INTO pockets (id, name, date_start, date_end, status, status_id, owner_user_id, department) VALUES
(101, 'Работа в огороде', '2025-12-16', NULL, 'Запущен', (SELECT id FROM statuses WHERE entity_type='pocket' AND code='running' LIMIT 1), 4, 'Личное хозяйство'),
(102, 'Постройка дома', '2025-12-20', NULL, 'Запущен', (SELECT id FROM statuses WHERE entity_type='pocket' AND code='running' LIMIT 1), 5, 'Строительный блок'),
(103, 'Выращивание скота', '2025-12-23', NULL, 'Запущен', (SELECT id FROM statuses WHERE entity_type='pocket' AND code='running' LIMIT 1), 6, 'Фермерский блок');

INSERT INTO projects (id, name, project_code, pocket_id, status, status_id, date_start, date_end, curator_business_user_id, curator_it_user_id) VALUES
(201, 'Подготовка грядок', 'OGR-01', 101, 'Активен', (SELECT id FROM statuses WHERE entity_type='project' AND code='active' LIMIT 1), '2025-12-16', NULL, 4, 3),
(202, 'Система полива', 'OGR-02', 101, 'Активен', (SELECT id FROM statuses WHERE entity_type='project' AND code='active' LIMIT 1), '2026-01-04', NULL, 4, 3),
(203, 'Теплица и рассада', 'OGR-03', 101, 'Активен', (SELECT id FROM statuses WHERE entity_type='project' AND code='active' LIMIT 1), '2026-01-12', NULL, 4, 3),
(204, 'Фундамент и дренаж', 'DOM-01', 102, 'Завершён', (SELECT id FROM statuses WHERE entity_type='project' AND code='done' LIMIT 1), '2025-12-20', '2026-02-02', 5, 3),
(205, 'Коробка и перекрытия', 'DOM-02', 102, 'Активен', (SELECT id FROM statuses WHERE entity_type='project' AND code='active' LIMIT 1), '2026-01-05', NULL, 5, 3),
(206, 'Кровля и фасад', 'DOM-03', 102, 'Активен', (SELECT id FROM statuses WHERE entity_type='project' AND code='active' LIMIT 1), '2026-01-20', NULL, 5, 3),
(207, 'Переоборудование хлева', 'SKT-01', 103, 'Активен', (SELECT id FROM statuses WHERE entity_type='project' AND code='active' LIMIT 1), '2025-12-23', NULL, 6, 2),
(208, 'Рацион и закупки', 'SKT-02', 103, 'Активен', (SELECT id FROM statuses WHERE entity_type='project' AND code='active' LIMIT 1), '2026-01-08', NULL, 6, 2),
(209, 'Ветеринарный контроль', 'SKT-03', 103, 'Активен', (SELECT id FROM statuses WHERE entity_type='project' AND code='active' LIMIT 1), '2026-01-25', NULL, 6, 2);

COMMIT;
