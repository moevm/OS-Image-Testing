SELECT
  'OS 1' AS lable,
  (item -> 'job options' -> 'bs') AS block_size,
  (item -> {{operation}} ->> 'iops_mean')::float AS iops
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
  (item->>'jobname') LIKE CONCAT('%seq_', {{operation}}, '%')
  [[ AND os = {{os1}} ]]
  [[ AND core_info = {{core_info1}} ]]
  [[ AND started_at BETWEEN {{start1}} AND {{end1}} ]]

UNION ALL

SELECT
  'OS 2' AS lable,
  (item -> 'job options' -> 'bs') AS block_size,
  (item -> {{operation}} ->> 'iops_mean')::float AS iops
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
  (item->>'jobname') LIKE CONCAT('%seq_', {{operation}}, '%')
  [[ AND os = {{os2}} ]]
  [[ AND core_info = {{core_info2}} ]]
  [[ AND CASE WHEN {{start2}} IS NULL THEN experiment.started_at BETWEEN {{start1}} AND {{end1}} ELSE experiment.started_at BETWEEN {{start2}} AND {{end2}} END ]]
