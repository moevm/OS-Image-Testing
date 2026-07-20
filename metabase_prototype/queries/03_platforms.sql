-- Distinct target platforms, optionally filtered by subsystem/profile
SELECT DISTINCT target_platform
FROM test_run
WHERE 1=1
AND {{subsystem}}
AND {{profile}}
ORDER BY 1;
