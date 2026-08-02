SELECT
	experiment.experiment_id,
	"configuration".os,
	"configuration".core_info,
	experiment.type,
	experiment.started_at,
	(result -> 'metrics' -> 'summary' ->> 'passed')::INT AS passed,
	(result -> 'metrics' -> 'summary' ->> 'failed')::INT AS failed,
	(result -> 'metrics' -> 'summary' ->> 'broken')::INT AS broken,
	(result -> 'metrics' -> 'summary' ->> 'skipped')::INT AS skipped,
	(result -> 'metrics' -> 'summary' ->> 'warnings')::INT AS warnings
FROM util_run_result AS l
JOIN experiment ON l.experiment_id = experiment.experiment_id
JOIN "configuration" ON experiment.config_id = "configuration".config_id
WHERE l.command LIKE '%kirk%'
  [[ AND os = {{os}} ]]
  [[ AND core_info = {{core_info}} ]]
  [[ AND experiment.started_at BETWEEN {{start}} AND {{end}} ]]
  [[ AND type = {{experiment_filter}} ]]
