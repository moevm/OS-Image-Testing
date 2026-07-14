SELECT
  experiment.experiment_id,
  configuration.os,
  ('seq_read') AS job_name,
  (item -> 'job options' -> 'bs') as block_size,
  (item -> 'read' ->> 'iops_mean')::float as iops
FROM
  (
    SELECT
      l.experiment_id,
      jsonb_array_elements(l.result::jsonb -> 'jobs') AS item
    FROM
      util_run_result AS l
    WHERE
      l.command LIKE '%fio%'
  ) subquery
  JOIN experiment ON subquery.experiment_id = experiment.experiment_id
  JOIN "configuration" ON experiment.config_id = configuration.config_id
WHERE
  (item->>'jobname') LIKE '%seq_read%'
  [[ AND os = {{os}} ]]
  [[ AND core_info = {{core_info}} ]]
  [[ AND started_at BETWEEN {{start}} AND {{end}} ]]

UNION ALL

SELECT
  experiment.experiment_id,
  configuration.os,
  ('seq_write') AS job_name,
  (item -> 'job options' -> 'bs') as block_size,
  (item -> 'write' ->> 'iops_mean')::float as iops
FROM
  (
    SELECT
      l.experiment_id,
      jsonb_array_elements(l.result::jsonb -> 'jobs') AS item
    FROM
      util_run_result AS l
    WHERE
      l.command LIKE '%fio%'
  ) subquery
  JOIN experiment ON subquery.experiment_id = experiment.experiment_id
  JOIN "configuration" ON experiment.config_id = configuration.config_id
WHERE
  (item->>'jobname') LIKE '%seq_write%'
  [[ AND os = {{os}} ]]
  [[ AND core_info = {{core_info}} ]]
  [[ AND started_at BETWEEN {{start}} AND {{end}} ]]
