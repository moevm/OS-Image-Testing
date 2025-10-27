#!/bin/bash

echo "Starting NETWORK stress test..."
stress-ng --sock 2 --sock-ops 2 --timeout 10 > stress-output.log 2>&1 &
STRESS_PID=$!

echo "nameserver $GOOGLE_DNS" >> /etc/resolv.conf
wget --timeout=10 "$GOOGLE_IP" > wget-output.log 2>&1 &
WGET_PID=$!

wait $WGET_PID
WGET_RESULT=$?
wait $STRESS_PID
STRESS_RESULT=$?

echo "= stress-ng output ="
cat stress-output.log
echo "= wget output ="
cat wget-output.log

rm stress-output.log wget-output.log

if [ $WGET_RESULT -eq 0 ] && [ $STRESS_RESULT -eq 0 ]; then
    echo "NETWORK test PASSED"
    exit 0
else
    echo "NETWORK test FAILED"
    exit 1
fi
