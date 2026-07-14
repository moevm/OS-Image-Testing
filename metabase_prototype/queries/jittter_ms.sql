SELECT
	((((l.result ->> 'client')::jsonb ->> 'end')::jsonb -> 'sum')::jsonb -> 'jitter_ms')::float AS jitter_ms,
	command,
    "configuration".os,
    "configuration".core_info,
    experiment.type,
    experiment.started_at,
    experiment.experiment_id
FROM util_run_result AS l
JOIN experiment ON l.experiment_id = experiment.experiment_id
JOIN "configuration" ON experiment.config_id = "configuration".config_id
WHERE l.command LIKE '%iperf3%'
  AND l.command LIKE '%--udp%'
  AND l.command NOT LIKE '%stress-ng%'
  AND JSON_EXISTS(l.result::jsonb, '$.client')
  [[ AND os = {{os}} ]]
  [[ AND core_info = {{core_info}} ]]
  [[ AND started_at BETWEEN {{start}} AND {{end}} ]]
  [[ AND type = {{experiment_filter}} ]]
