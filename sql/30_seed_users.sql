PRAGMA foreign_keys = ON;
BEGIN TRANSACTION;

INSERT INTO users (id, login, full_name, role, is_active, status_id) VALUES
(1, 'mozzy', 'Иванов Степан Иванович', 'admin', 1, (SELECT id FROM statuses WHERE entity_type='user' AND code='active' LIMIT 1)),
(2, 'head_farm', 'Соколов Андрей Петрович', 'head', 1, (SELECT id FROM statuses WHERE entity_type='user' AND code='active' LIMIT 1)),
(3, 'lead_build', 'Кузнецов Олег Сергеевич', 'teamlead', 1, (SELECT id FROM statuses WHERE entity_type='user' AND code='active' LIMIT 1)),
(4, 'curator_garden', 'Петрова Василиса Васильевна', 'curator', 1, (SELECT id FROM statuses WHERE entity_type='user' AND code='active' LIMIT 1)),
(5, 'curator_house', 'Смирнов Максим Игоревич', 'curator', 1, (SELECT id FROM statuses WHERE entity_type='user' AND code='active' LIMIT 1)),
(6, 'curator_livestock', 'Орлова Наталья Дмитриевна', 'curator', 1, (SELECT id FROM statuses WHERE entity_type='user' AND code='active' LIMIT 1)),
(7, 'exec_soil', 'Грачев Николай Артемович', 'executor', 1, (SELECT id FROM statuses WHERE entity_type='user' AND code='active' LIMIT 1)),
(8, 'exec_irrigation', 'Морозова Елена Викторовна', 'executor', 1, (SELECT id FROM statuses WHERE entity_type='user' AND code='active' LIMIT 1)),
(9, 'exec_mason', 'Федоров Павел Андреевич', 'executor', 1, (SELECT id FROM statuses WHERE entity_type='user' AND code='active' LIMIT 1)),
(10, 'exec_roof', 'Волкова Мария Константиновна', 'executor', 1, (SELECT id FROM statuses WHERE entity_type='user' AND code='active' LIMIT 1)),
(11, 'exec_vet', 'Лебедев Илья Романович', 'executor', 1, (SELECT id FROM statuses WHERE entity_type='user' AND code='active' LIMIT 1)),
(12, 'exec_feed', 'Зайцева Анна Валерьевна', 'executor', 1, (SELECT id FROM statuses WHERE entity_type='user' AND code='active' LIMIT 1)),
(13, 'exec_general', 'Белов Кирилл Олегович', 'executor', 1, (SELECT id FROM statuses WHERE entity_type='user' AND code='active' LIMIT 1)),
(14, 'archived_worker', 'Тихонова Ольга Сергеевна', 'executor', 0, (SELECT id FROM statuses WHERE entity_type='user' AND code='inactive' LIMIT 1));

COMMIT;
