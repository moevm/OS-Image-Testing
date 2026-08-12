-- Scalar metrics for boxplot
SELECT
    benchmark,
    measure,
    metric_key,
    unit,
    n,
    q1,
    median,
    q3,
    min_value,
    max_value,
    avg_value,
    stddev_value
FROM v_scalar_boxplot
WHERE 1=1
AND {{subsystem}}
AND {{profile}}
AND {{target_platform}}
AND {{os_version}}
AND {{tool}}
AND {{metric_key}}
ORDER BY 1, 2, 3;
