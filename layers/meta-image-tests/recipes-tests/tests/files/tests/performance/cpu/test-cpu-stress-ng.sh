#!/bin/bash

perf stat -e cycles,instructions,context-switches,cpu-migrations,page-faults,cpu-clock -- stress-ng --cpu 0 --cpu-method matrixprod --timeout 60 --metrics-brief
