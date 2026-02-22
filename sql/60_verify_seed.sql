SELECT 'users' AS entity, COUNT(*) AS total FROM users
UNION ALL
SELECT 'pockets', COUNT(*) FROM pockets
UNION ALL
SELECT 'projects', COUNT(*) FROM projects
UNION ALL
SELECT 'tasks', COUNT(*) FROM tasks
UNION ALL
SELECT 'task_pauses', COUNT(*) FROM task_pauses
UNION ALL
SELECT 'action_log', COUNT(*) FROM action_log;

SELECT id, login, full_name, role, is_active
FROM users
ORDER BY id;

SELECT COUNT(*) AS admin_total
FROM users
WHERE role = 'admin';

SELECT login AS admin_login
FROM users
WHERE role = 'admin'
ORDER BY id;

SELECT name
FROM pockets
ORDER BY id;

SELECT p.id, p.name, pk.name AS pocket_name
FROM projects p
JOIN pockets pk ON pk.id = p.pocket_id
ORDER BY p.id;

SELECT s.name AS task_status, COUNT(*) AS total
FROM tasks t
JOIN statuses s ON s.id = t.status_id AND s.entity_type = 'task'
GROUP BY s.name
ORDER BY s.sort_order;

SELECT t.id, t.description, s.name AS status_name, t.executor_user_id, p.name AS project_name, pk.name AS pocket_name
FROM tasks t
JOIN statuses s ON s.id = t.status_id AND s.entity_type = 'task'
JOIN projects p ON p.id = t.project_id
JOIN pockets pk ON pk.id = p.pocket_id
ORDER BY t.id;

SELECT COUNT(*) AS paused_tasks_without_pause
FROM tasks t
JOIN statuses s ON s.id = t.status_id AND s.entity_type = 'task' AND s.code = 'paused'
LEFT JOIN task_pauses tp ON tp.task_id = t.id
WHERE tp.id IS NULL;

SELECT al.id, al.timestamp, u.login, al.entity_type, al.entity_id, al.action_type, al.comment
FROM action_log al
JOIN users u ON u.id = al.user_id
ORDER BY al.id;
