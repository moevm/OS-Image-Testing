-- Scalar metrics summary table
SELECT
    benchmark,
    measure,
    metric_key,
    unit,
    AVG(value) AS avg_value,
    MIN(value) AS min_value,
    MAX(value) AS max_value,
    stddev_samp(value) AS stddev_value,
    COUNT(*) AS samples
FROM v_scalar_metabase
WHERE 1=1
AND {{subsystem}}
AND {{profile}}
AND {{target_platform}}
AND {{os_version}}
AND {{tool}}
AND {{metric_key}}
AND {{started_at}}
GROUP BY 1, 2, 3, 4
ORDER BY 1, 2;
