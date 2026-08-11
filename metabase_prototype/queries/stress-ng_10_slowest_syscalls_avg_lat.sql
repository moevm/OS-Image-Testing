WITH
  parsed_data AS (
    SELECT
      experiment.experiment_id,
      CONFIGURATION.os,
      CONFIGURATION.core_info,
      experiment.started_at,
      result ->> 'tool' AS tool,
      result -> 'time' ->> 'duration_sec' AS duration_sec,
      result -> 'metrics' AS metrics_raw,
      json_typeof(result -> 'metrics') AS metrics_type
    FROM
      util_run_result
      LEFT JOIN experiment ON util_run_result.experiment_id = experiment.experiment_id
      LEFT JOIN "configuration" ON experiment.config_id = CONFIGURATION.config_id
    WHERE
      result ->> 'tool' = 'stress-ng'
	  [[ AND configuration.os = {{os}} ]]
	  [[ AND experiment.started_at BETWEEN {{start}} AND {{end}} ]]
  ),
  expanded_metrics AS (
    SELECT
      experiment_id,
      os,
      metrics_value
    FROM
      parsed_data,
      json_each(metrics_raw) AS metrics (metrics_key, metrics_value)
    WHERE
      metrics_type = 'object'
      AND metrics_value -> 'top10_slowest' IS NOT NULL
      AND json_typeof(metrics_value -> 'top10_slowest') = 'array'
  ),
  all_syscalls AS (
    SELECT
      experiment_id,
      os,
      (top10_item ->> 1)::float AS avg_time_ns
    FROM
      expanded_metrics,
      json_array_elements(metrics_value -> 'top10_slowest') AS top10_item
  ),
  experiment_avg AS (
    SELECT
      experiment_id,
      os,
      AVG(avg_time_ns) AS exp_avg_time_ns,
      COUNT(*) AS syscalls_count
    FROM
      all_syscalls
    GROUP BY
      experiment_id,
      os
  )
SELECT
  os,
  ROUND(exp_avg_time_ns / 1000000.0) AS "avg_dur_ms"
FROM
  experiment_avg
ORDER BY
  os,
  exp_avg_time_ns DESC;
