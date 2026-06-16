-- Distinct OS versions, optionally filtered by subsystem/profile/platform
SELECT DISTINCT os_version
FROM test_run
WHERE 1=1
AND {{subsystem}}
AND {{profile}}
AND {{target_platform}}
ORDER BY 1;
