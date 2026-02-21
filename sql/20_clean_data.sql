PRAGMA foreign_keys = ON;
BEGIN TRANSACTION;

DELETE FROM action_log;
DELETE FROM task_pauses;
DELETE FROM tasks;
DELETE FROM projects;
DELETE FROM pockets;
DELETE FROM users;

DELETE FROM sqlite_sequence
WHERE name IN ('users', 'pockets', 'projects', 'tasks', 'task_pauses', 'action_log');

COMMIT;
