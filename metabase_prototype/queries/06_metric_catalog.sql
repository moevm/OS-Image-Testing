-- Distinct metrics available for the selected slice
SELECT DISTINCT
    metric_type,
    benchmark,
    measure,
    metric_key,
    unit
FROM v_metric_catalog
WHERE 1=1
AND {{subsystem}}
AND {{profile}}
AND {{target_platform}}
AND {{os_version}}
AND {{tool}}
ORDER BY 1, 2, 3;
