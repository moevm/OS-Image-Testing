SELECT l.experiment_id, configuration.config_id,
	os, core_info, type, l.started_at, l.ended_at, jsonb_array_elements(l.result::jsonb)
FROM util_run_result AS l
JOIN experiment ON l.experiment_id = experiment.experiment_id
JOIN "configuration" ON experiment.config_id = configuration.config_id
WHERE command LIKE '%systemctl%'
  [[ AND os = {{os}} ]]
  [[ AND core_info = {{core_info}} ]]
  [[ AND started_at BETWEEN {{start}} AND {{end}} ]]
  [[ AND type = {{experiment_filter}} ]]
ORDER BY l.experiment_id
