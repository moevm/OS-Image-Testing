SELECT
    (interval_item->'sum'->>'start')::float AS interval_start,
    (interval_item->'sum'->>'bits_per_second')::float AS bits_per_second,
    "configuration".os,
    "configuration".core_info,
    experiment.type,
    experiment.started_at,
    l.command,
    experiment.experiment_id,
    -- уникальная метка для каждого варианта запуска
    experiment.experiment_id::text || ': ' || 
        CASE 
            WHEN l.command LIKE '%--udp%' THEN 'UDP'
            WHEN l.command LIKE '%--tcp%' THEN 'TCP'
            ELSE 'iperf3'
        END AS experiment_label
FROM loader AS l
JOIN experiment ON l.experiment_id = experiment.experiment_id
JOIN "configuration" ON experiment.config_id = "configuration".config_id
CROSS JOIN LATERAL jsonb_array_elements(
    (l.result::jsonb)->'client'->'intervals'
) AS interval_item
WHERE l.command LIKE '%iperf3%'
  [[ AND {{os}} ]]
  [[ AND {{core_info}} ]]
  [[ AND {{type}} ]]
  [[ AND {{date_range}} ]]
ORDER BY interval_start
