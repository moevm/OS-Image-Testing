SELECT
  label,
  block_size,
  iops,
  operation_type
FROM (
  SELECT
    CONCAT('OS 1') AS label,
    block_size,
    CASE 
      WHEN job_name LIKE '%rand_write%' THEN (item -> 'write' ->> 'iops_mean')::float
      WHEN job_name LIKE '%rand_read%' THEN (item -> 'read' ->> 'iops_mean')::float
      WHEN job_name LIKE '%seq_write%' THEN (item -> 'write' ->> 'iops_mean')::float
      WHEN job_name LIKE '%seq_read%' THEN (item -> 'read' ->> 'iops_mean')::float
      ELSE 0
    END as iops,
    job_name as operation_type
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
  WHERE 
    os = {{os1}}
    [[ AND started_at BETWEEN {{start1}} AND {{end1}} ]]
  
  UNION ALL
  
  SELECT
    CONCAT('OS 2') AS label,
    block_size,
    CASE 
      WHEN job_name LIKE '%rand_write%' THEN (item -> 'write' ->> 'iops_mean')::float
      WHEN job_name LIKE '%rand_read%' THEN (item -> 'read' ->> 'iops_mean')::float
      WHEN job_name LIKE '%seq_write%' THEN (item -> 'write' ->> 'iops_mean')::float
      WHEN job_name LIKE '%seq_read%' THEN (item -> 'read' ->> 'iops_mean')::float
      ELSE 0
    END as iops,
    job_name as operation_type
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
  WHERE 
    os = {{os2}}
	[[ AND started_at BETWEEN {{start2}} AND {{end2}} ]]
) AS combined_results
