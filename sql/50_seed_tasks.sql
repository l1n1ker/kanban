PRAGMA foreign_keys = ON;
BEGIN TRANSACTION;

INSERT INTO tasks (id, description, project_id, status, status_id, date_created, date_start_work, date_done, executor_user_id, customer, code_link) VALUES
(301, 'Разметить грядки под ранние культуры', 201, 'Создана', (SELECT id FROM statuses WHERE entity_type='task' AND code='created' LIMIT 1), '2026-02-11', NULL, NULL, NULL, 'Семья', 'https://wiki.local/garden/beds-layout'),
(302, 'Перекопать участок и внести компост', 201, 'В работе', (SELECT id FROM statuses WHERE entity_type='task' AND code='in_progress' LIMIT 1), '2026-02-02', '2026-02-04', NULL, 7, 'Семья', 'https://wiki.local/garden/compost'),
(303, 'Подготовить теплые грядки под огурцы', 201, 'Приостановлена', (SELECT id FROM statuses WHERE entity_type='task' AND code='paused' LIMIT 1), '2026-01-30', '2026-02-01', NULL, 8, 'Семья', NULL),
(304, 'Собрать и вывезти старую ботву', 201, 'Завершена', (SELECT id FROM statuses WHERE entity_type='task' AND code='done' LIMIT 1), '2026-01-20', '2026-01-22', '2026-01-29', 13, 'Семья', NULL),

(305, 'Установить накопительную бочку у теплицы', 202, 'Создана', (SELECT id FROM statuses WHERE entity_type='task' AND code='created' LIMIT 1), '2026-02-12', NULL, NULL, 8, 'Семья', NULL),
(306, 'Проложить магистральную ПНД-трубу', 202, 'В работе', (SELECT id FROM statuses WHERE entity_type='task' AND code='in_progress' LIMIT 1), '2026-02-01', '2026-02-03', NULL, 8, 'Семья', 'https://wiki.local/garden/irrigation-mainline'),
(307, 'Подключить капельные линии к грядкам', 202, 'Приостановлена', (SELECT id FROM statuses WHERE entity_type='task' AND code='paused' LIMIT 1), '2026-01-29', '2026-02-02', NULL, 7, 'Семья', NULL),
(308, 'Настроить таймер полива на 3 зоны', 202, 'Завершена', (SELECT id FROM statuses WHERE entity_type='task' AND code='done' LIMIT 1), '2026-01-15', '2026-01-18', '2026-01-27', 8, 'Семья', NULL),

(309, 'Закупить грунт и кассеты для рассады', 203, 'Создана', (SELECT id FROM statuses WHERE entity_type='task' AND code='created' LIMIT 1), '2026-02-13', NULL, NULL, NULL, 'Семья', NULL),
(310, 'Смонтировать стеллажи в теплице', 203, 'В работе', (SELECT id FROM statuses WHERE entity_type='task' AND code='in_progress' LIMIT 1), '2026-01-31', '2026-02-05', NULL, 13, 'Семья', NULL),
(311, 'Организовать досветку над рассадой', 203, 'Приостановлена', (SELECT id FROM statuses WHERE entity_type='task' AND code='paused' LIMIT 1), '2026-01-28', '2026-02-01', NULL, 10, 'Семья', 'https://wiki.local/garden/light'),
(312, 'Провести обработку теплицы от плесени', 203, 'Завершена', (SELECT id FROM statuses WHERE entity_type='task' AND code='done' LIMIT 1), '2026-01-14', '2026-01-16', '2026-01-25', 13, 'Семья', NULL),

(313, 'Согласовать вывоз грунта после копки', 204, 'Создана', (SELECT id FROM statuses WHERE entity_type='task' AND code='created' LIMIT 1), '2026-02-06', NULL, NULL, NULL, 'Семья', NULL),
(314, 'Проверить дренажные каналы после дождя', 204, 'В работе', (SELECT id FROM statuses WHERE entity_type='task' AND code='in_progress' LIMIT 1), '2026-01-28', '2026-01-30', NULL, 9, 'Семья', NULL),
(315, 'Усилить опалубку на северной стенке', 204, 'Приостановлена', (SELECT id FROM statuses WHERE entity_type='task' AND code='paused' LIMIT 1), '2026-01-21', '2026-01-23', NULL, 9, 'Семья', NULL),
(316, 'Залить бетон в центральную ленту', 204, 'Завершена', (SELECT id FROM statuses WHERE entity_type='task' AND code='done' LIMIT 1), '2026-01-08', '2026-01-10', '2026-01-18', 9, 'Семья', 'https://wiki.local/build/foundation'),

(317, 'Подготовить список материалов на стены', 205, 'Создана', (SELECT id FROM statuses WHERE entity_type='task' AND code='created' LIMIT 1), '2026-02-12', NULL, NULL, 13, 'Семья', NULL),
(318, 'Смонтировать балки перекрытия 1 этажа', 205, 'В работе', (SELECT id FROM statuses WHERE entity_type='task' AND code='in_progress' LIMIT 1), '2026-02-03', '2026-02-06', NULL, 9, 'Семья', NULL),
(319, 'Выставить армопояс под перекрытие', 205, 'Приостановлена', (SELECT id FROM statuses WHERE entity_type='task' AND code='paused' LIMIT 1), '2026-01-30', '2026-02-02', NULL, 9, 'Семья', NULL),
(320, 'Закрыть монтаж чернового перекрытия', 205, 'Завершена', (SELECT id FROM statuses WHERE entity_type='task' AND code='done' LIMIT 1), '2026-01-17', '2026-01-20', '2026-01-31', 9, 'Семья', NULL),

(321, 'Согласовать цвет фасадной панели', 206, 'Создана', (SELECT id FROM statuses WHERE entity_type='task' AND code='created' LIMIT 1), '2026-02-14', NULL, NULL, NULL, 'Семья', NULL),
(322, 'Уложить подкладочный ковер кровли', 206, 'В работе', (SELECT id FROM statuses WHERE entity_type='task' AND code='in_progress' LIMIT 1), '2026-02-04', '2026-02-07', NULL, 10, 'Семья', NULL),
(323, 'Установить снегозадержатели на скате', 206, 'Приостановлена', (SELECT id FROM statuses WHERE entity_type='task' AND code='paused' LIMIT 1), '2026-01-31', '2026-02-03', NULL, 10, 'Семья', NULL),
(324, 'Смонтировать водосточную систему', 206, 'Завершена', (SELECT id FROM statuses WHERE entity_type='task' AND code='done' LIMIT 1), '2026-01-18', '2026-01-22', '2026-02-01', 10, 'Семья', NULL),

(325, 'Составить перечень ремонта стойл', 207, 'Создана', (SELECT id FROM statuses WHERE entity_type='task' AND code='created' LIMIT 1), '2026-02-10', NULL, NULL, 11, 'Ферма', NULL),
(326, 'Заменить вентиляцию в хлеве', 207, 'В работе', (SELECT id FROM statuses WHERE entity_type='task' AND code='in_progress' LIMIT 1), '2026-02-02', '2026-02-05', NULL, 13, 'Ферма', NULL),
(327, 'Починить поилки в секции молодняка', 207, 'Приостановлена', (SELECT id FROM statuses WHERE entity_type='task' AND code='paused' LIMIT 1), '2026-01-27', '2026-02-01', NULL, 11, 'Ферма', NULL),
(328, 'Утеплить северную стену хлева', 207, 'Завершена', (SELECT id FROM statuses WHERE entity_type='task' AND code='done' LIMIT 1), '2026-01-12', '2026-01-15', '2026-01-26', 13, 'Ферма', NULL),

(329, 'Собрать коммерческие предложения по кормам', 208, 'Создана', (SELECT id FROM statuses WHERE entity_type='task' AND code='created' LIMIT 1), '2026-02-11', NULL, NULL, 12, 'Ферма', NULL),
(330, 'Обновить недельный рацион стада', 208, 'В работе', (SELECT id FROM statuses WHERE entity_type='task' AND code='in_progress' LIMIT 1), '2026-02-01', '2026-02-04', NULL, 12, 'Ферма', 'https://wiki.local/livestock/feed-plan'),
(331, 'Закупить витаминные добавки на месяц', 208, 'Приостановлена', (SELECT id FROM statuses WHERE entity_type='task' AND code='paused' LIMIT 1), '2026-01-28', '2026-01-31', NULL, 12, 'Ферма', NULL),
(332, 'Сформировать график поставок комбикорма', 208, 'Завершена', (SELECT id FROM statuses WHERE entity_type='task' AND code='done' LIMIT 1), '2026-01-14', '2026-01-16', '2026-01-24', 12, 'Ферма', NULL),

(333, 'Подготовить график весенней вакцинации', 209, 'Создана', (SELECT id FROM statuses WHERE entity_type='task' AND code='created' LIMIT 1), '2026-02-09', NULL, NULL, 11, 'Ферма', NULL),
(334, 'Провести осмотр телят и занести карточки', 209, 'В работе', (SELECT id FROM statuses WHERE entity_type='task' AND code='in_progress' LIMIT 1), '2026-02-03', '2026-02-06', NULL, 11, 'Ферма', NULL),
(335, 'Организовать повторный осмотр проблемной группы', 209, 'Приостановлена', (SELECT id FROM statuses WHERE entity_type='task' AND code='paused' LIMIT 1), '2026-01-31', '2026-02-02', NULL, 11, 'Ферма', NULL),
(336, 'Закрыть журнал плановых прививок', 209, 'Завершена', (SELECT id FROM statuses WHERE entity_type='task' AND code='done' LIMIT 1), '2026-01-10', '2026-01-13', '2026-01-23', 11, 'Ферма', NULL);

COMMIT;
