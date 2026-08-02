SELECT l.experiment_id, configuration.config_id,
	os, core_info, type, l.description, l.started_at, l.ended_at, l.result::jsonb::INT AS jctl_error_count
FROM util_run_result AS l
JOIN experiment ON l.experiment_id = experiment.experiment_id
JOIN "configuration" ON experiment.config_id = configuration.config_id
WHERE command LIKE CONCAT('%journalctl%', {{ error }}, '%')
  [[ AND os = {{os}} ]]
  [[ AND core_info = {{core_info}} ]]
  [[ AND started_at BETWEEN {{start}} AND {{end}} ]]
  [[ AND type = {{experiment_filter}} ]]
ORDER BY l.experiment_id
