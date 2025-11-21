#!/bin/bash

echo "Starting FWTS tests..."
fwts

code=$?
if [ $code -eq 0 ]; then
    echo "FWTS tests PASSED"
    exit 0
else
    echo "Some tests FAILED"
    exit 1
fi
