SELECT 'OS 1' AS experiment_label, service, avg_time FROM (
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
			[[ AND os = {{os1}} ]]
		    [[ AND core_info = {{core_info}} ]]
		    [[ AND started_at BETWEEN {{start1}} AND {{end1}} ]]
	) subquery
	WHERE item->>'service_name'IS NOT NULL
	GROUP BY service
	LIMIT 5
)

UNION ALL

SELECT 'OS 2' AS experiment_label, service, avg_time FROM (
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
			[[ AND os = {{os2}} ]]
			[[ AND core_info = {{core_info2}} ]]
			[[ AND CASE WHEN {{start2}} IS NULL THEN started_at BETWEEN {{start1}} AND {{end1}} ELSE started_at BETWEEN {{start2}} AND {{end2}} END ]]
	) subquery
	WHERE item->>'service_name'IS NOT NULL
	GROUP BY service
	LIMIT 5
)
