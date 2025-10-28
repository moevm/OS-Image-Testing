#!/bin/bash

echo "Starting HDD stress test for 10 seconds..."
stress-ng --hdd 1 --hdd-bytes 100M --timeout 10 --hdd-opts sync

code=$?
if [ $code -eq 0 ]; then
    echo "DISK test PASSED"
    exit 0
else
    echo "DISK test FAILED"
    exit 1
fi
