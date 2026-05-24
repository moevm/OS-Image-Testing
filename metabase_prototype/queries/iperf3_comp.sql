SELECT
    (interval_item->'sum'->>'start')::float AS interval_start,
    (interval_item->'sum'->>'bits_per_second')::float AS bits_per_second,
    'Experiment 1' AS experiment_label,
    "configuration".os AS os,
    "configuration".core_info AS core_info,
    experiment.started_at
FROM loader AS l
JOIN experiment ON l.experiment_id = experiment.experiment_id
JOIN "configuration" ON experiment.config_id = "configuration".config_id
CROSS JOIN LATERAL jsonb_array_elements(
    (l.result::jsonb)->'client'->'intervals'
) AS interval_item
WHERE l.command LIKE '%iperf3%'
  [[ AND {{os1}} ]]
  [[ AND {{core_info1}} ]]
  [[ AND {{date1}} ]]
  [[ AND {{type}} ]]

UNION ALL

SELECT
    (interval_item->'sum'->>'start')::float AS interval_start,
    (interval_item->'sum'->>'bits_per_second')::float AS bits_per_second,
    'Experiment 2' AS experiment_label,
    "configuration".os,
    "configuration".core_info,
    experiment.started_at
FROM loader AS l
JOIN experiment ON l.experiment_id = experiment.experiment_id
JOIN "configuration" ON experiment.config_id = "configuration".config_id
CROSS JOIN LATERAL jsonb_array_elements(
    (l.result::jsonb)->'client'->'intervals'
) AS interval_item
WHERE l.command LIKE '%iperf3%'
  [[ AND {{os2}} ]]
  [[ AND {{core_info2}} ]]
  [[ AND {{date2}} ]]
  [[ AND {{type}} ]]

ORDER BY interval_start