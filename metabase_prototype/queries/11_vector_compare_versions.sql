-- Compare OS versions on one vector metric
SELECT
    point_ts AS "time",
    os_version,
    target_platform,
    series,
    value
FROM v_vector_metabase
WHERE 1=1
AND {{subsystem}}
AND {{profile}}
AND {{target_platform}}
AND {{tool}}
AND {{metric_key}}
AND {{point_ts}}
ORDER BY 1, 2, 3, 4;
