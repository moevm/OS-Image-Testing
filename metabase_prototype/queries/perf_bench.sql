SELECT
	-- Add here another metrics as columns if needed
    (item->>'benchmark') AS benchmark,
    (item->>'total_time')::float AS total_time,
    (item->>'usecs_per_op')::float AS usecs_per_op,
    (item->>'ops_per_sec')::bigint AS ops_per_sec,
    (item->>'gb_per_sec_default')::float AS gb_per_sec_default,
    (item->>'gb_per_sec_unrolled')::float AS gb_per_sec_unrolled
FROM (
    SELECT jsonb_array_elements(
        CASE
            WHEN jsonb_typeof(l.result::jsonb) = 'array' THEN l.result::jsonb
            WHEN jsonb_typeof(l.result::jsonb) = 'object' THEN l.result::jsonb->'perf_metrics'
            ELSE '[]'::jsonb
        END
    ) AS item
    FROM loader AS l
    JOIN experiment ON l.experiment_id = experiment.experiment_id
    JOIN "configuration" ON experiment.config_id = configuration.config_id
    WHERE l.command LIKE '%perf bench%'
      [[ AND {{os}} ]]
      [[ AND {{core_info}} ]]
      [[ AND {{type}} ]]
      [[ AND {{date_range}} ]]
      [[ AND l.command LIKE CONCAT('%', {{command}}, '%') ]]
) subquery
WHERE item->>'benchmark' IS NOT NULL
ORDER BY benchmark;
