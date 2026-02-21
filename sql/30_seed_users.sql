PRAGMA foreign_keys = ON;
BEGIN TRANSACTION;

INSERT INTO users (id, login, full_name, role, is_active, status_id) VALUES
(1, 'mozzy', 'Mozzy Admin', 'admin', 1, (SELECT id FROM statuses WHERE entity_type='user' AND name='Активен' LIMIT 1)),
(2, 'head_1', 'Head One', 'head', 1, (SELECT id FROM statuses WHERE entity_type='user' AND name='Активен' LIMIT 1)),
(3, 'curator_1', 'Curator One', 'curator', 1, (SELECT id FROM statuses WHERE entity_type='user' AND name='Активен' LIMIT 1)),
(4, 'curator_2', 'Curator Two', 'curator', 1, (SELECT id FROM statuses WHERE entity_type='user' AND name='Активен' LIMIT 1)),
(5, 'curator_3', 'Curator Three', 'curator', 1, (SELECT id FROM statuses WHERE entity_type='user' AND name='Активен' LIMIT 1)),
(6, 'exec_01', 'Executor 01', 'executor', 1, (SELECT id FROM statuses WHERE entity_type='user' AND name='Активен' LIMIT 1)),
(7, 'exec_02', 'Executor 02', 'executor', 1, (SELECT id FROM statuses WHERE entity_type='user' AND name='Активен' LIMIT 1)),
(8, 'exec_03', 'Executor 03', 'executor', 1, (SELECT id FROM statuses WHERE entity_type='user' AND name='Активен' LIMIT 1)),
(9, 'exec_04', 'Executor 04', 'executor', 1, (SELECT id FROM statuses WHERE entity_type='user' AND name='Активен' LIMIT 1)),
(10, 'exec_05', 'Executor 05', 'executor', 1, (SELECT id FROM statuses WHERE entity_type='user' AND name='Активен' LIMIT 1)),
(11, 'exec_06', 'Executor 06', 'executor', 1, (SELECT id FROM statuses WHERE entity_type='user' AND name='Активен' LIMIT 1)),
(12, 'exec_07', 'Executor 07', 'executor', 1, (SELECT id FROM statuses WHERE entity_type='user' AND name='Активен' LIMIT 1)),
(13, 'exec_08', 'Executor 08', 'executor', 1, (SELECT id FROM statuses WHERE entity_type='user' AND name='Активен' LIMIT 1)),
(14, 'exec_09', 'Executor 09', 'executor', 1, (SELECT id FROM statuses WHERE entity_type='user' AND name='Активен' LIMIT 1)),
(15, 'exec_10', 'Executor 10', 'executor', 1, (SELECT id FROM statuses WHERE entity_type='user' AND name='Активен' LIMIT 1));

COMMIT;
