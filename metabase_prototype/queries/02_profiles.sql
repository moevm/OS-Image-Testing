-- Distinct profiles, optionally filtered by subsystem
SELECT DISTINCT profile
FROM test_run
WHERE 1=1
AND {{subsystem}}
ORDER BY 1;
