SELECT os_lable,
	AVG(total_time) AS avg_total,
	AVG(userspace_time) AS avg_userspace,
	AVG(kernel_time) AS avg_kernel
FROM (
	SELECT
	    "configuration".os,
	    experiment.started_at,
	    experiment.experiment_id,
		'OS 1' AS os_lable,
		(result->>'total_time')::float AS total_time,
	    (result->>'userspace_time')::float AS userspace_time,
	    (result->>'kernel_time')::float AS kernel_time
	FROM util_run_result AS l
	JOIN experiment ON l.experiment_id = experiment.experiment_id
	JOIN "configuration" ON experiment.config_id = "configuration".config_id
	WHERE l.command LIKE '%systemd-analyze time%'
		[[ AND os = {{os1}} ]]
		[[ AND core_info = {{core_info}} ]]
		[[ AND experiment.started_at BETWEEN {{start1}} AND {{end1}} ]]
)
GROUP BY os_lable

UNION ALL

SELECT os_lable,
	AVG(total_time) AS avg_total,
	AVG(userspace_time) AS avg_userspace,
	AVG(kernel_time) AS avg_kernel
FROM (
	SELECT
	    "configuration".os,
	    experiment.started_at,
	    experiment.experiment_id,
		'OS 2' AS os_lable,
		(result->>'total_time')::float AS total_time,
	    (result->>'userspace_time')::float AS userspace_time,
	    (result->>'kernel_time')::float AS kernel_time
	FROM util_run_result AS l
	JOIN experiment ON l.experiment_id = experiment.experiment_id
	JOIN "configuration" ON experiment.config_id = "configuration".config_id
	WHERE l.command LIKE '%systemd-analyze time%'
		[[ AND os = {{os2}} ]]
		[[ AND core_info = {{core_info2}} ]]
		[[ AND CASE WHEN {{start2}} IS NULL THEN experiment.started_at BETWEEN {{start1}} AND {{end1}} ELSE experiment.started_at BETWEEN {{start2}} AND {{end2}} END ]]
)
GROUP BY os_lable
