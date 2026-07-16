SELECT
  experiment.experiment_id,
  configuration.os,
  ('seq_read') AS job_name,
  block_size,
  (item -> 'read' ->> 'iops_mean')::float as iops
FROM
  (
	SELECT
	  l.experiment_id,
	  (l.result::jsonb -> 'test_type' -> 'detailed' ->> 'bs') AS block_size,
	  (l.result::jsonb -> 'test_type' ->> 'name') AS job_name,
	  (l.result::jsonb ->> 'metrics')::jsonb AS item
	FROM
	  util_run_result AS l
	WHERE
	  l.command LIKE '%fio%'
  ) subquery
  JOIN experiment ON subquery.experiment_id = experiment.experiment_id
  JOIN "configuration" ON experiment.config_id = configuration.config_id
WHERE job_name LIKE '%seq_read%'
  [[ AND os = {{os}} ]]
  [[ AND configuration.core_info = {{core_info}} ]]
  [[ AND experiment.started_at BETWEEN {{start}} AND {{end}} ]]
  [[ AND type = {{experiment_filter}} ]]

UNION ALL

SELECT
  experiment.experiment_id,
  configuration.os,
  ('seq_write') AS job_name,
  block_size,
  (item -> 'write' ->> 'iops_mean')::float as iops
FROM
  (
	SELECT
	  l.experiment_id,
	  (l.result::jsonb -> 'test_type' -> 'detailed' ->> 'bs') AS block_size,
	  (l.result::jsonb -> 'test_type' ->> 'name') AS job_name,
	  (l.result::jsonb ->> 'metrics')::jsonb AS item
	FROM
	  util_run_result AS l
	WHERE
	  l.command LIKE '%fio%'
  ) subquery
  JOIN experiment ON subquery.experiment_id = experiment.experiment_id
  JOIN "configuration" ON experiment.config_id = configuration.config_id
WHERE job_name LIKE '%seq_write%'
  [[ AND os = {{os}} ]]
  [[ AND configuration.core_info = {{core_info}} ]]
  [[ AND experiment.started_at BETWEEN {{start}} AND {{end}} ]]
  [[ AND type = {{experiment_filter}} ]]
