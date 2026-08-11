SELECT 'OS 1' AS os, syscall, dur_ms FROM (
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
				  [[ AND os = {{os1}} ]]
				  [[ AND core_info = {{core_info1}} ]]
				  [[ AND started_at BETWEEN {{start1}} AND {{end1}} ]]
				  [[ AND type = {{type}} ]]
		) WHERE metrics::text LIKE '%top10_slowest%' AND metrics::jsonb ->> 'top10_slowest' IS NOT NULL
	)
	GROUP BY syscall
	ORDER BY dur_ms DESC
	LIMIT 10
)

UNION ALL

SELECT 'OS 2' AS os, syscall, dur_ms FROM (
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
				  [[ AND os = {{os2}} ]]
				  [[ AND core_info = {{core_info2}} ]]
				  [[ AND CASE WHEN {{start2}} IS NULL THEN started_at BETWEEN {{start1}} AND {{end1}} ELSE started_at BETWEEN {{start2}} AND {{end2}} END ]]
				  [[ AND type = {{type}} ]]
		) WHERE metrics::text LIKE '%top10_slowest%' AND metrics::jsonb ->> 'top10_slowest' IS NOT NULL
	)
	GROUP BY syscall
	ORDER BY dur_ms DESC
	LIMIT 10
)
