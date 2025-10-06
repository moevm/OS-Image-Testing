#!/bin/bash

perf stat -e block:block_rq_issue,block:block_rq_complete,block:block_rq_insert,block:block_io_done,cycles,instructions,cpu-clock \
  -- stress-ng --io 4 --timeout 60s --metrics-brief

