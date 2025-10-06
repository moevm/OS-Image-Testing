#!/bin/bash

perf stat -e net:net_dev_xmit,net:netif_rx,syscalls:sys_enter_sendto,syscalls:sys_enter_recvfrom -a -- stress-ng --sock 3 --timeout 60s --metrics-brief
