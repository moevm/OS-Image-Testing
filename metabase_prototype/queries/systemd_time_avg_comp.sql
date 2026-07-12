SELECT os, 
AVG(total_time) AS avg_total, 
AVG(userspace_time) AS avg_userspace, 
AVG(kernel_time) AS avg_kernel
FROM (
	SELECT
	    "configuration".os,
	    experiment.started_at,
	    experiment.experiment_id,
		result,
		(result->>'total_time')::float AS total_time,
	    (result->>'userspace_time')::float AS userspace_time,
	    (result->>'kernel_time')::float AS kernel_time
	FROM util_run_result AS l
	JOIN experiment ON l.experiment_id = experiment.experiment_id
	JOIN "configuration" ON experiment.config_id = "configuration".config_id
	WHERE l.command LIKE '%systemd-analyze time%'
)
GROUP BY os