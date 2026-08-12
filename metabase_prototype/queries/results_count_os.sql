SELECT experiment_id, experiment.config_id,
	os, core_info, type, started_at, ended_at,
	tests_total, tests_passed, tests_failed, tests_skipped, tests_broken
FROM experiment
JOIN "configuration" ON experiment.config_id = "configuration".config_id
WHERE 1=1
  [[ AND os = {{os}} ]]
  [[ AND core_info = {{core_info}} ]]
  [[ AND started_at BETWEEN {{start}} AND {{end}} ]]
  [[ AND type = {{experiment_filter}} ]]
ORDER BY experiment_id
