SELECT item->>'service_name' AS service, AVG((item->>'slow_time_s')::float) AS avg_time
FROM (
	SELECT
	    "configuration".os,
	    experiment.started_at,
		command,
		jsonb_array_elements(l.result::jsonb) AS item
	FROM util_run_result AS l
	JOIN experiment ON l.experiment_id = experiment.experiment_id
	JOIN "configuration" ON experiment.config_id = "configuration".config_id
	WHERE l.command LIKE '%systemd-analyze critical-chain%'
		[[ AND os = {{os}} ]]
	    [[ AND core_info = {{core_info}} ]]
	    [[ AND experiment.started_at BETWEEN {{start}} AND {{end}} ]]
) subquery
WHERE item->>'service_name'IS NOT NULL
GROUP BY service
LIMIT 10
