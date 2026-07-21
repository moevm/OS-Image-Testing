SELECT (metrics::jsonb ->> 'test') as test_fnq, (metrics::jsonb ->> 'duration')::float as duration,
	'Experiment 1' AS experiment_label,
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
		  [[ AND os = {{os1}} ]]
		  [[ AND core_info = {{core_info1}} ]]
		  [[ AND started_at BETWEEN {{start1}} AND {{end1}} ]]
		  [[ AND type = {{type}} ]]
	), LATERAL json_each_text(item)
)

UNION ALL

SELECT (metrics::jsonb ->> 'test') as test_fnq, (metrics::jsonb ->> 'duration')::float as duration,
	'Experiment 2' AS experiment_label,
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
		  [[ AND os = {{os2}} ]]
		  [[ AND core_info = {{core_info2}} ]]
		  [[ AND CASE WHEN {{start2}} IS NULL THEN started_at BETWEEN {{start1}} AND {{end1}} ELSE started_at BETWEEN {{start2}} AND {{end2}} END ]]
		  [[ AND type = {{type}} ]]
	), LATERAL json_each_text(item)
)
