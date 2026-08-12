-- Vector metric time series
SELECT
    point_ts AS "time",
    target_platform,
    os_version,
    series,
    value,
    lower_value,
    upper_value
FROM v_vector_metabase
WHERE 1=1
AND {{subsystem}}
AND {{profile}}
AND {{target_platform}}
AND {{os_version}}
AND {{tool}}
AND {{metric_key}}
AND {{point_ts}}
ORDER BY 1, 2, 3, 4;
