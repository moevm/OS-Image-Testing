#!/bin/bash


perf stat -e syscalls:sys_enter_newstat,syscalls:sys_enter_newlstat,syscalls:sys_enter_newfstatat,syscalls:sys_enter_openat,context-switches,minor-faults find /tmp -name "nonexistentfile"
