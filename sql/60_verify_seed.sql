SELECT 'users' AS entity, COUNT(*) AS total FROM users
UNION ALL
SELECT 'pockets', COUNT(*) FROM pockets
UNION ALL
SELECT 'projects', COUNT(*) FROM projects
UNION ALL
SELECT 'tasks', COUNT(*) FROM tasks;

SELECT id, login, role, is_active FROM users ORDER BY id;

SELECT
    t.id,
    t.description,
    t.status,
    t.executor_user_id,
    p.name AS project_name,
    pk.name AS pocket_name
FROM tasks t
JOIN projects p ON p.id = t.project_id
JOIN pockets pk ON pk.id = p.pocket_id
ORDER BY t.id;
