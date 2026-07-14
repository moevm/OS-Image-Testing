SELECT
    "configuration".os,
    "configuration".core_info,
    experiment.type,
    experiment.started_at,
    experiment.experiment_id,
	command,
	(result->>'total_time')::float AS total_time,
    (result->>'userspace_time')::float AS userspace_time,
    (result->>'kernel_time')::float AS kernel_time
FROM util_run_result AS l
JOIN experiment ON l.experiment_id = experiment.experiment_id
JOIN "configuration" ON experiment.config_id = "configuration".config_id
WHERE l.command LIKE '%systemd-analyze time%'
    [[ AND os = {{os}} ]]
    [[ AND core_info = {{core_info}} ]]
    [[ AND started_at BETWEEN {{start}} AND {{end}} ]]
