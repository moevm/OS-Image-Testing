SELECT interval_start, AVG(bits_per_second) as bits_per_second FROM (
	SELECT
		(interval_item->'sum'->>'start')::float AS interval_start,
	    (interval_item->'sum'->>'bits_per_second')::float AS bits_per_second,
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
		  [[ AND os = {{os}} ]]
		  [[ AND core_info = {{core_info}} ]]
		  [[ AND experiment.started_at BETWEEN {{start}} AND {{end}} ]]
		  [[ AND type = {{type}} ]]
	) CROSS JOIN LATERAL jsonb_array_elements(
	    metrics::jsonb -> 'client' -> 'intervals'
	) AS interval_item
) GROUP BY interval_start
