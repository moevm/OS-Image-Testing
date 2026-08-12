SELECT
	experiment.experiment_id,
	"configuration".os,
	"configuration".core_info,
	experiment.type,
	experiment.started_at,
	REPLACE((result -> 'metrics' -> 'summary' ->> 'skipped'), '-1', '0')::INT as skipped,
	REPLACE((result -> 'metrics' -> 'summary' ->> 'passed'), '-1', '0')::INT as passed,
	REPLACE((result -> 'metrics' -> 'summary' ->> 'failed'), '-1', '0')::INT as failed,
	REPLACE((result -> 'metrics' -> 'summary' ->> 'metrics_untrustworthy'), '-1', '0')::INT as metrics_untrustworthy
FROM util_run_result AS l
JOIN experiment ON l.experiment_id = experiment.experiment_id
JOIN "configuration" ON experiment.config_id = "configuration".config_id
WHERE l.command LIKE '%stress-ng%' AND (result -> 'metrics' ->> 'summary') IS NOT NULL
  [[ AND os = {{os}} ]]
  [[ AND core_info = {{core_info}} ]]
  [[ AND experiment.started_at BETWEEN {{start}} AND {{end}} ]]
  [[ AND type = {{experiment_filter}} ]]
