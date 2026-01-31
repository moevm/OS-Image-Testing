#!/usr/bin/env bash

echo "Starting NETWORK stress test..."
stress-ng --sock 2 --sock-ops 2 --timeout 10 > stress-output.log 2>&1 &
STRESS_PID=$!

if [ -n "${GOOGLE_DNS:-}" ]; then
  echo "nameserver ${GOOGLE_DNS}" >> /etc/resolv.conf 2>/dev/null || true
fi

wget --timeout=10 --tries=1 "${GOOGLE_IP:-http://142.250.185.206/}" > wget-output.log 2>&1 &
WGET_PID=$!

wait "$WGET_PID"
WGET_RESULT=$?
wait "$STRESS_PID"
STRESS_RESULT=$?

echo "= stress-ng output ="
cat stress-output.log
echo "= wget output ="
cat wget-output.log

rm -f stress-output.log wget-output.log

if [ "$WGET_RESULT" -eq 0 ] && [ "$STRESS_RESULT" -eq 0 ]; then
    echo "NETWORK test PASSED"
    exit 0
else
    echo "NETWORK test FAILED"
    exit 1
fi

