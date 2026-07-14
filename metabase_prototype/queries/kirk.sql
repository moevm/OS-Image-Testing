SELECT (metrics::jsonb ->> 'test') as test_fnq, (metrics::jsonb ->> 'duration')::float as duration,
	os,
	core_info,
	type,
	started_at,
	experiment_id
FROM (
	SELECT value as metrics,
	    os,
	    core_info,
	    type,
	    started_at,
	    experiment_id
	FROM (
		SELECT
		    (result -> 'metrics') as item,
		    "configuration".os,
		    "configuration".core_info,
		    experiment.type,
		    experiment.started_at,
		    experiment.experiment_id
		FROM util_run_result AS l
		JOIN experiment ON l.experiment_id = experiment.experiment_id
		JOIN "configuration" ON experiment.config_id = "configuration".config_id
		WHERE l.command LIKE '%kirk%'
		  [[ AND os = {{os}} ]]
		  [[ AND core_info = {{core_info}} ]]
		  [[ AND experiment.started_at BETWEEN {{start}} AND {{end}} ]]
		  [[ AND type = {{experiment_filter}} ]]
	), LATERAL json_each_text(item)
)
