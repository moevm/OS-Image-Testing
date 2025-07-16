#!/bin/bash

perf stat -e syscalls:sys_enter_newfstatat,syscalls:sys_enter_openat,context-switches,minor-faults find /bin -name "nonexistentfile"
