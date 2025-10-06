#!/bin/bash

perf stat -e page-faults,minor-faults,major-faults,context-switches -- stress-ng --vm 1 --vm-bytes 10% --timeout 60s --metrics-brief


