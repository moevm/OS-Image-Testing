SELECT benchmark, experiment_label,
	AVG(total_time) AS total_time_avg,
	AVG(usecs_per_op) AS usecs_per_op_avg,
	AVG(ops_per_sec) AS ops_per_sec_avg,
	AVG(gb_per_sec_default) AS gb_per_sec_default_avg,
	AVG(gb_per_sec_unrolled) AS gb_per_sec_unrolled_avg
FROM (

SELECT
	-- Add here another metrics as columns if needed
    (item->>'benchmark') AS benchmark,
    (CASE
      WHEN (item->>'duration_sec') IS NOT NULL THEN (item->>'duration_sec')::float
      ELSE (item->>'total_time')::float
    END) AS total_time,
    (item->>'usecs_per_op')::float AS usecs_per_op,
    (item->>'ops_per_sec')::bigint AS ops_per_sec,
    (item->>'gb_per_sec_default')::float AS gb_per_sec_default,
    (item->>'gb_per_sec_unrolled')::float AS gb_per_sec_unrolled, experiment.experiment_id, os, core_info,
	'Experiment 1' AS experiment_label
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
      [[ AND os = {{os1}} ]]
      [[ AND core_info = {{core_info1}} ]]
      [[ AND experiment.started_at BETWEEN {{start1}} AND {{end1}} ]]
      [[ AND l.command LIKE CONCAT('%', {{command}}, '%') ]]
) AS subquery
JOIN experiment ON subquery.experiment_id = experiment.experiment_id

)

GROUP BY experiment_label, benchmark

UNION ALL

SELECT benchmark, experiment_label,
	AVG(total_time) AS total_time_avg,
	AVG(usecs_per_op) AS usecs_per_op_avg,
	AVG(ops_per_sec) AS ops_per_sec_avg,
	AVG(gb_per_sec_default) AS gb_per_sec_default_avg,
	AVG(gb_per_sec_unrolled) AS gb_per_sec_unrolled_avg
FROM (

SELECT
	-- Add here another metrics as columns if needed
    (item->>'benchmark') AS benchmark,
    (CASE
      WHEN (item->>'duration_sec') IS NOT NULL THEN (item->>'duration_sec')::float
      ELSE (item->>'total_time')::float
    END) AS total_time,
    (item->>'usecs_per_op')::float AS usecs_per_op,
    (item->>'ops_per_sec')::bigint AS ops_per_sec,
    (item->>'gb_per_sec_default')::float AS gb_per_sec_default,
    (item->>'gb_per_sec_unrolled')::float AS gb_per_sec_unrolled, experiment.experiment_id, os, core_info,
	'Experiment 2' AS experiment_label
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
      [[ AND os = {{os2}} ]]
      [[ AND core_info = {{core_info2}} ]]
      [[ AND CASE WHEN {{start2}} IS NULL THEN experiment.started_at BETWEEN {{start1}} AND {{end1}} ELSE experiment.started_at BETWEEN {{start2}} AND {{end2}} END ]]
      [[ AND l.command LIKE CONCAT('%', {{command}}, '%') ]]
) AS subquery
JOIN experiment ON subquery.experiment_id = experiment.experiment_id

)

GROUP BY experiment_label, benchmark
