#!/bin/sh

echo "Starting MEMORY stress test for 10 seconds..."
stress-ng --vm 2 --vm-bytes 256M --timeout 10

if [ $? -eq 0 ]; then
    echo "CPU test PASSED"
    exit 0
else
    echo "CPU test FAILED"
    exit 1
fi