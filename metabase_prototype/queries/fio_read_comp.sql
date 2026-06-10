SELECT
  sub.experiment_id,
  "configuration".os,
  "configuration".core_info,
  experiment.type,
  experiment.started_at,
  sub.item ->> 'jobname' AS job_name,
  (CASE
    WHEN {{metric}} = 'min' THEN NULLIF((sub.item -> 'read' -> 'lat_ns' ->> 'min')::float, 0)
    WHEN {{metric}} = 'max' THEN NULLIF((sub.item -> 'read' -> 'lat_ns' ->> 'max')::float, 0)
    WHEN {{metric}} = 'stddev' THEN NULLIF((sub.item -> 'read' -> 'lat_ns' ->> 'stddev')::float, 0)
    ELSE NULLIF((sub.item -> 'read' -> 'lat_ns' ->> 'mean')::float, 0)
  END) / 1000000.0 AS read_latency_ms,
  'Experiment 1' AS experiment_label
FROM (
  SELECT
    l.experiment_id,
    jsonb_array_elements(l.result::jsonb -> 'jobs') AS item
  FROM loader AS l
  WHERE l.command LIKE '%fio%'
) sub
JOIN experiment ON sub.experiment_id = experiment.experiment_id
JOIN "configuration" ON experiment.config_id = "configuration".config_id
WHERE (sub.item ->> 'jobname') LIKE '%read%'
  [[ AND os = {{os1}} ]]
  [[ AND core_info = {{core_info1}} ]]
  [[ AND started_at BETWEEN {{start1}} AND {{end1}} ]]
  [[ AND type = {{type}} ]]

UNION ALL

SELECT
  sub.experiment_id,
  "configuration".os,
  "configuration".core_info,
  experiment.type,
  experiment.started_at,
  sub.item ->> 'jobname' AS job_name,
  (CASE
    WHEN {{metric}} = 'min' THEN NULLIF((sub.item -> 'read' -> 'lat_ns' ->> 'min')::float, 0)
    WHEN {{metric}} = 'max' THEN NULLIF((sub.item -> 'read' -> 'lat_ns' ->> 'max')::float, 0)
    WHEN {{metric}} = 'stddev' THEN NULLIF((sub.item -> 'read' -> 'lat_ns' ->> 'stddev')::float, 0)
    ELSE NULLIF((sub.item -> 'read' -> 'lat_ns' ->> 'mean')::float, 0)
  END) / 1000000.0 AS read_latency_ms,
  'Experiment 2' AS experiment_label
FROM (
  SELECT
    l.experiment_id,
    jsonb_array_elements(l.result::jsonb -> 'jobs') AS item
  FROM loader AS l
  WHERE l.command LIKE '%fio%'
) sub
JOIN experiment ON sub.experiment_id = experiment.experiment_id
JOIN "configuration" ON experiment.config_id = "configuration".config_id
WHERE (sub.item ->> 'jobname') LIKE '%read%'
  [[ AND os = {{os2}} ]]
  [[ AND core_info = {{core_info2}} ]]
  [[ AND CASE WHEN {{start2}} IS NULL THEN started_at BETWEEN {{start1}} AND {{end1}} ELSE started_at BETWEEN {{start2}} AND {{end2}} END ]]
  [[ AND type = {{type}} ]]

ORDER BY job_name;
