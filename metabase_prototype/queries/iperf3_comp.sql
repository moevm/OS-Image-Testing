SELECT
	(interval_item->'sum'->>'start')::float AS interval_start,
	(interval_item->'sum'->>'bits_per_second')::float AS bits_per_second,
	'Experiment 1' as experiment_label,
	os,
	core_info,
	type,
	started_at,
	experiment_id
FROM (
	SELECT
		result ->> 'metrics' as metrics,
		"configuration".os,
		"configuration".core_info,
		experiment.type,
		experiment.started_at,
		l.command,
		experiment.experiment_id
	FROM util_run_result AS l
	JOIN experiment ON l.experiment_id = experiment.experiment_id
	JOIN "configuration" ON experiment.config_id = "configuration".config_id
	WHERE l.command LIKE '%iperf3%'
	  AND (result ->> 'tool') = 'iperf3'
	  [[ AND os = {{os1}} ]]
	  [[ AND core_info = {{core_info1}} ]]
	  [[ AND started_at BETWEEN {{start1}} AND {{end1}} ]]
	  [[ AND type = {{type}} ]]
) CROSS JOIN LATERAL jsonb_array_elements(
	metrics::jsonb -> 'client' -> 'intervals'
) AS interval_item

UNION ALL

SELECT
	(interval_item->'sum'->>'start')::float AS interval_start,
	(interval_item->'sum'->>'bits_per_second')::float AS bits_per_second,
	'Experiment 1' as experiment_label,
	os,
	core_info,
	type,
	started_at,
	experiment_id
FROM (
	SELECT
		result ->> 'metrics' as metrics,
		"configuration".os,
		"configuration".core_info,
		experiment.type,
		experiment.started_at,
		l.command,
		experiment.experiment_id
	FROM util_run_result AS l
	JOIN experiment ON l.experiment_id = experiment.experiment_id
	JOIN "configuration" ON experiment.config_id = "configuration".config_id
	WHERE l.command LIKE '%iperf3%'
	  AND (result ->> 'tool') = 'iperf3'
	  [[ AND os = {{os2}} ]]
	  [[ AND core_info = {{core_info2}} ]]
	  [[ AND CASE WHEN {{start2}} IS NULL THEN started_at BETWEEN {{start1}} AND {{end1}} ELSE started_at BETWEEN {{start2}} AND {{end2}} END ]]
	  [[ AND type = {{type}} ]]
) CROSS JOIN LATERAL jsonb_array_elements(
	metrics::jsonb -> 'client' -> 'intervals'
) AS interval_item

ORDER BY interval_start
