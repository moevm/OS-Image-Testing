#!/bin/bash

echo "Starting MEMORY stress test for 10 seconds..."
stress-ng --vm 2 --vm-bytes 16M --timeout 10

code=$?
if [ $code -eq 0 ]; then
    echo "MEMORY test PASSED"
    exit 0
else
    echo "MEMORY test FAILED"
    exit 1
fi
