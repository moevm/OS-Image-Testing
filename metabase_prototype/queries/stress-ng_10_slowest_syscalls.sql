SELECT slowest[0] AS syscall, AVG((CASE
	WHEN {{ metric }} = 'avg' THEN slowest[1]
	WHEN {{ metric }} = 'min' THEN slowest[2]
	WHEN {{ metric }} = 'max' THEN slowest[3]
END)::float) / 1000000 AS dur_ms
FROM (
	SELECT jsonb_array_elements((metrics::jsonb ->> 'top10_slowest')::jsonb) as slowest, os, core_info, type, started_at, experiment_id FROM (
		SELECT
			value as metrics,
			"configuration".os,
			"configuration".core_info,
			experiment.type,
			experiment.started_at,
			l.command,
			experiment.experiment_id
		FROM util_run_result AS l
		CROSS JOIN LATERAL json_each_text(result -> 'metrics')
		JOIN experiment ON l.experiment_id = experiment.experiment_id
		JOIN "configuration" ON experiment.config_id = "configuration".config_id
		WHERE l.command LIKE '%stress-ng%'
		  AND l.command LIKE '%--syscall%'
		  AND result::text LIKE '%top10_slowest%'
		  [[ AND os = {{os}} ]]
		  [[ AND core_info = {{core_info}} ]]
		  [[ AND experiment.started_at BETWEEN {{start}} AND {{end}} ]]
		  [[ AND type = {{type}} ]]
	) WHERE metrics::text LIKE '%top10_slowest%' AND metrics::jsonb ->> 'top10_slowest' IS NOT NULL
)
GROUP BY syscall
ORDER BY dur_ms DESC
LIMIT 10
