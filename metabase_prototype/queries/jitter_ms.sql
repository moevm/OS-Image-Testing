SELECT
	((((metrics -> 'client')::jsonb ->> 'end')::jsonb -> 'sum')::jsonb -> 'jitter_ms')::float AS jitter_ms,
	command,
    os,
    core_info,
    type,
    started_at,
    experiment_id
FROM (
	SELECT
		(result ->> 'metrics')::jsonb as metrics,
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
	  AND l.command LIKE '%--udp%'
	  AND l.command NOT LIKE '%stress-ng%'
	  -- AND JSON_EXISTS(l.result::jsonb, '$.client')
	  [[ AND os = {{os}} ]]
	  [[ AND core_info = {{core_info}} ]]
	  [[ AND experiment.started_at BETWEEN {{start}} AND {{end}} ]]
	  [[ AND type = {{type}} ]]
)
