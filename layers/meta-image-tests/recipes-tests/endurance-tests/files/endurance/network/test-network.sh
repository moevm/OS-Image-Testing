#!/bin/bash

echo "Starting NETWORK stress test for 10 seconds..."
stress-ng --sock 2 --sock-ops 2 --timeout 10

echo "nameserver $GOOGLE_DNS" >> /etc/resolv.conf
wget --timeout=10 $GOOGLE_IP

if [ $? -eq 0 ]; then
    echo "NETWORK test PASSED"
    exit 0
else
    echo "NETWORK test FAILED"
    exit 1
fi