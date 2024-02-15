  -- https://community.home-assistant.io/t/how-to-reduce-your-database-size-and-extend-the-life-of-your-sd-card/205299/
  -- https://community.home-assistant.io/t/find-most-frequently-updated-sensor/302102/
  
  SELECT
    table_name,
    pg_size_pretty(pg_total_relation_size(quote_ident(table_name))),
    pg_relation_size(quote_ident(table_name))
  FROM information_schema.tables
  WHERE table_schema = 'public'
  ORDER BY 3 DESC;
  
  SELECT
      s.metadata_id,
      m.entity_id,
      COUNT(*) AS cnt
  FROM states AS s
  LEFT JOIN states_meta AS m
  ON s.metadata_id = m.metadata_id
  GROUP BY
      s.metadata_id,
      m.entity_id
  ORDER BY
      COUNT(*) DESC;
  
  SELECT
      (shared_data::json->>'entity_id') AS entity_id,
      COUNT(*) AS cnt
  FROM event_data
  WHERE
      shared_data::json->>'entity_id' IS NOT NULL
  GROUP BY
      (shared_data::json->>'entity_id')
  HAVING COUNT(*) > 1
  ORDER BY
      COUNT(*) DESC;

----------

-- https://community.home-assistant.io/t/how-to-keep-your-recorder-database-size-under-control/295795/204

SELECT 
  COUNT(state_id) AS cnt, 
  COUNT(state_id) * 100 / (
    SELECT 
      COUNT(state_id) 
    FROM 
      states
  ) AS cnt_pct, 
  SUM(
    LENGTH(state_attributes.shared_attrs)
  ) AS bytes, 
  SUM(
    LENGTH(state_attributes.shared_attrs)
  ) * 100 / (
    SELECT 
      SUM(
        LENGTH(state_attributes.shared_attrs)
      ) 
    FROM 
      states
  ) AS bytes_pct, 
  states_meta.entity_id 
FROM 
  states 
LEFT JOIN state_attributes ON states.attributes_id = state_attributes.attributes_id
LEFT JOIN states_meta ON states.metadata_id = states_meta.metadata_id
GROUP BY 
  states_meta.entity_id, 
  states.metadata_id 
ORDER BY 
  cnt DESC;
