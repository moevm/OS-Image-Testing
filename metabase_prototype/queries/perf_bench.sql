SELECT
	-- Add here another metrics as columns if needed
    (item->>'benchmark') AS benchmark,
    (item->>'total_time')::float AS total_time,
    (item->>'usecs_per_op')::float AS usecs_per_op,
    (item->>'ops_per_sec')::bigint AS ops_per_sec,
    (item->>'gb_per_sec_default')::float AS gb_per_sec_default,
    (item->>'gb_per_sec_unrolled')::float AS gb_per_sec_unrolled, experiment.experiment_id, os, core_info
FROM (
    SELECT jsonb_array_elements(CASE
		WHEN jsonb_typeof(l.result::jsonb) = 'array' THEN l.result::jsonb
		WHEN jsonb_typeof(l.result::jsonb) = 'object' AND l.result::jsonb ?? 'perf_metrics' AND jsonb_typeof(l.result::jsonb->'perf_metrics') = 'array' THEN l.result::jsonb->'perf_metrics'
		WHEN jsonb_typeof(l.result::jsonb) = 'object' AND l.result::jsonb ?? 'perf_metrics' AND jsonb_typeof(l.result::jsonb->'perf_metrics') = 'object' THEN json_array((l.result::jsonb->'perf_metrics'->'test_type')::jsonb || (l.result::jsonb->'perf_metrics'->'time')::jsonb || (l.result::jsonb->'perf_metrics'->'metrics')::jsonb)
		WHEN jsonb_typeof(l.result::jsonb) = 'object' AND l.result::jsonb ?? 'test_type' THEN json_array((l.result::jsonb->'test_type')::jsonb || (l.result::jsonb->'time')::jsonb || (l.result::jsonb->'metrics')::jsonb)
		ELSE '[]'::jsonb
	END) AS item, experiment.experiment_id, os, core_info
    FROM util_run_result AS l
    JOIN experiment ON l.experiment_id = experiment.experiment_id
    JOIN "configuration" ON experiment.config_id = configuration.config_id
    WHERE l.command LIKE '%perf bench%'
      [[ AND os = {{os}} ]]
      [[ AND core_info = {{core_info}} ]]
      [[ AND started_at BETWEEN {{start}} AND {{end}} ]]
      [[ AND type = {{experiment_filter}} ]]
      [[ AND l.command LIKE CONCAT('%', {{command}}, '%') ]]
) subquery
JOIN experiment ON subquery.experiment_id = experiment.experiment_id
WHERE item->>'benchmark' IS NOT NULL AND ((item->>'total_time')::float IS NOT NULL OR (item->>'usecs_per_op')::float IS NOT NULL OR (item->>'ops_per_sec')::float IS NOT NULL OR (item->>'gb_per_sec_default')::float IS NOT NULL OR (item->>'gb_per_sec_unrolled')::float IS NOT NULL)
ORDER BY benchmark;
