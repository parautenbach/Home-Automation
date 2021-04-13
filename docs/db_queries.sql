-- List databases: \l
-- All tables: \dt
-- Describe table: \d events

SELECT (pg_database_size('homeassistant')/1024/1024) as db_size;

SELECT pg_size_pretty(pg_total_relation_size('events'));
SELECT pg_size_pretty(pg_total_relation_size('states'));

SELECT event_type, COUNT(*) AS count FROM events GROUP BY event_type ORDER BY count DESC;
SELECT domain, COUNT(*) AS count FROM states GROUP BY domain ORDER BY count DESC;

SELECT entity_id, COUNT(*) AS count FROM states WHERE domain='sensor' GROUP BY entity_id ORDER BY count DESC;
