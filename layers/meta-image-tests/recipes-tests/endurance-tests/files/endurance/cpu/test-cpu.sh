#!/bin/bash

echo "Starting CPU stress test for 10 seconds..."
stress-ng --cpu 0 --timeout 10 --metrics --verify

code=$?
if [ $code -eq 0 ]; then
    echo "CPU test PASSED"
    exit 0
else
    echo "CPU test FAILED"
    exit 1
fi
