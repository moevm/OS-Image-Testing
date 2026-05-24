SELECT
    (test_item->>'test_fqn') AS test_fqn,
    (test_item->'test'->>'duration')::float AS duration,
    'Experiment 1' AS experiment_label
FROM loader AS l
JOIN experiment ON l.experiment_id = experiment.experiment_id
JOIN "configuration" ON experiment.config_id = "configuration".config_id
CROSS JOIN LATERAL jsonb_array_elements(
    (l.result::jsonb)->'results'
) AS test_item
WHERE l.command LIKE '%kirk%'
  AND test_item->'test'->>'duration' IS NOT NULL
  [[ AND {{os1}} ]]
  [[ AND {{core_info1}} ]]
  [[ AND {{date1}} ]]
  [[ AND {{type}} ]]

UNION ALL

SELECT
    (test_item->>'test_fqn') AS test_fqn,
    (test_item->'test'->>'duration')::float AS duration,
    'Experiment 2' AS experiment_label
FROM loader AS l
JOIN experiment ON l.experiment_id = experiment.experiment_id
JOIN "configuration" ON experiment.config_id = "configuration".config_id
CROSS JOIN LATERAL jsonb_array_elements(
    (l.result::jsonb)->'results'
) AS test_item
WHERE l.command LIKE '%kirk%'
  AND test_item->'test'->>'duration' IS NOT NULL
  [[ AND {{os2}} ]]
  [[ AND {{core_info2}} ]]
  [[ AND {{date2}} ]]
  [[ AND {{type}} ]]

ORDER BY test_fqn;