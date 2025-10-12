#!/bin/bash

perf stat -e context-switches,cpu-migrations,page-faults,cpu-clock -- stress-ng --cpu 0 --cpu-method matrixprod --timeout 60 --metrics-brief --oom-avoid
