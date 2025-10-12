#!/bin/bash

perf stat -e block:block_rq_issue,block:block_rq_complete,block:block_rq_insert,block:block_io_done,cpu-clock -- stress-ng --hdd 2 --hdd-bytes 100M --timeout 60s --metrics-brief --oom-avoid

