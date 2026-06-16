SELECT
  experiment.experiment_id,
  configuration.os,
  configuration.core_info,
  (item ->> 'jobname') AS job_name,
  (CASE
    WHEN {{metric}} = 'min' THEN NULLIF((item -> 'read' -> 'lat_ns' ->> 'min')::float, 0)
    WHEN {{metric}} = 'max' THEN NULLIF((item -> 'read' -> 'lat_ns' ->> 'max')::float, 0)
    WHEN {{metric}} = 'stddev' THEN NULLIF((item -> 'read' -> 'lat_ns' ->> 'stddev')::float, 0)
    ELSE NULLIF((item -> 'read' -> 'lat_ns' ->> 'mean')::float, 0) -- по умолчанию среднее
  END) / 1000000.0 AS read_latency_ms
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
  1 = 1
  AND (item->>'jobname') LIKE '%read%'
  [[ AND os = {{os}} ]]
  [[ AND core_info = {{core_info}} ]]
  [[ AND started_at BETWEEN {{start}} AND {{end}} ]]
  [[ AND type = {{experiment_filter}} ]]
ORDER BY
  job_name;
