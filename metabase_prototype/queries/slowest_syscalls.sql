SELECT test_fqn, AVG(duration) as duration_avg FROM (
	SELECT
	    (test_item->>'test_fqn') AS test_fqn,
	    (test_item->'test'->>'duration')::float AS duration,
	    "configuration".os,
	    "configuration".core_info,
	    experiment.type,
	    experiment.started_at,
	    experiment.experiment_id
	FROM util_run_result AS l
	JOIN experiment ON l.experiment_id = experiment.experiment_id
	JOIN "configuration" ON experiment.config_id = "configuration".config_id
	CROSS JOIN LATERAL jsonb_array_elements(
	    (l.result::jsonb)->'results'
	) AS test_item
	WHERE l.command LIKE '%kirk%'
	  AND test_item->'test'->>'duration' IS NOT NULL
	  [[ AND os = {{os}} ]]
	  [[ AND core_info = {{core_info}} ]]
	  [[ AND started_at BETWEEN {{start}} AND {{end}} ]]
	  [[ AND type = {{experiment_filter}} ]]
) GROUP BY test_fqn
ORDER BY duration_avg DESC
LIMIT 10
