SELECT
	-- Add here another metrics as columns if needed
    (item->>'benchmark') AS benchmark,
    (item->>'total_time')::float AS total_time,
    (item->>'usecs_per_op')::float AS usecs_per_op,
    (item->>'ops_per_sec')::bigint AS ops_per_sec,
    (item->>'gb_per_sec_default')::float AS gb_per_sec_default,
    (item->>'gb_per_sec_unrolled')::float AS gb_per_sec_unrolled,
    'Experiment 1' AS experiment_label
FROM (
    SELECT jsonb_array_elements(
        CASE
            WHEN jsonb_typeof(l.result::jsonb) = 'array' THEN l.result::jsonb
            WHEN jsonb_typeof(l.result::jsonb) = 'object' THEN l.result::jsonb->'perf_metrics'
            ELSE '[]'::jsonb
        END
    ) AS item
    FROM util_run_result AS l
    JOIN experiment ON l.experiment_id = experiment.experiment_id
    JOIN "configuration" ON experiment.config_id = configuration.config_id
    WHERE l.command LIKE '%perf bench%'
      [[ AND os = {{os1}} ]]
      [[ AND core_info = {{core_info1}} ]]
      [[ AND started_at BETWEEN {{start1}} AND {{end1}} ]]
      [[ AND type = {{type}} ]]
      [[ AND l.command LIKE CONCAT('%', {{command}}, '%') ]]
) AS experiment_label
WHERE item->>'benchmark' IS NOT NULL


UNION ALL

SELECT
	-- Add here another metrics as columns if needed
    (item->>'benchmark') AS benchmark,
    (item->>'total_time')::float AS total_time,
    (item->>'usecs_per_op')::float AS usecs_per_op,
    (item->>'ops_per_sec')::bigint AS ops_per_sec,
    (item->>'gb_per_sec_default')::float AS gb_per_sec_default,
    (item->>'gb_per_sec_unrolled')::float AS gb_per_sec_unrolled,
    'Experiment 2' AS experiment_label
FROM (
    SELECT jsonb_array_elements(
        CASE
            WHEN jsonb_typeof(l.result::jsonb) = 'array' THEN l.result::jsonb
            WHEN jsonb_typeof(l.result::jsonb) = 'object' THEN l.result::jsonb->'perf_metrics'
            ELSE '[]'::jsonb
        END
    ) AS item
    FROM util_run_result AS l
    JOIN experiment ON l.experiment_id = experiment.experiment_id
    JOIN "configuration" ON experiment.config_id = configuration.config_id
    WHERE l.command LIKE '%perf bench%'
      [[ AND os = {{os2}} ]]
      [[ AND core_info = {{core_info2}} ]]
      [[ AND CASE WHEN {{start2}} IS NULL THEN started_at BETWEEN {{start1}} AND {{end1}} ELSE started_at BETWEEN {{start2}} AND {{end2}} END ]]
      [[ AND type = {{type}} ]]
      [[ AND l.command LIKE CONCAT('%', {{command}}, '%') ]]
)
WHERE item->>'benchmark' IS NOT NULL

ORDER BY benchmark;
