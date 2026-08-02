SELECT
  experiment.experiment_id,
  configuration.os,
  configuration.core_info,
  type,
  job_name,
  (CASE
    WHEN {{metric}} = 'min' THEN NULLIF((item ->> 'min')::float, 0)
    WHEN {{metric}} = 'max' THEN NULLIF((item ->> 'max')::float, 0)
    WHEN {{metric}} = 'stddev' THEN NULLIF((item ->> 'stddev')::float, 0)
    ELSE NULLIF((item ->> 'mean')::float, 0) -- по умолчанию среднее
  END) / 1000000.0 AS read_latency_ms
FROM
  (
    SELECT
      l.experiment_id,
	  (l.result::jsonb -> 'test_type' ->> 'name') AS job_name,
      (l.result::jsonb -> 'metrics' -> 'write' -> 'lat_ns') AS item
    FROM
      util_run_result AS l
    WHERE
      l.command LIKE '%fio%'
  ) subquery
  JOIN experiment ON subquery.experiment_id = experiment.experiment_id
  JOIN "configuration" ON experiment.config_id = configuration.config_id
WHERE job_name LIKE '%write%'
  [[ AND os = {{os}} ]]
  [[ AND configuration.core_info = {{core_info}} ]]
  [[ AND experiment.started_at BETWEEN {{start}} AND {{end}} ]]
  [[ AND type = {{experiment_filter}} ]]
