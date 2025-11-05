#!/bin/bash

screen -L -Logfile /tmp/results/screen.log -h 10000 -dmS qemu runqemu qemux86-64 slirp nographic && \
timeout 120 bash -c '
until grep -q "root@qemux86-64" /tmp/results/screen.log 2>/dev/null; do
    sleep 5
    echo "Waiting for system to boot..."
done'

code=$?
if [ $code -eq 0 ]; then
    {
        echo 'Running tests...'
        screen -S qemu -X stuff 'ptest-runner -t 7200\n' && \
        timeout 7200 bash -c '
        until grep -q "STOP: ptest-runner" /tmp/results/screen.log 2>/dev/null; do
            sleep 5
            echo "Ptest running..."
        done'

	screen -S qemu -X stuff 'fwts; echo "FWTS tests completed"\n' && \
	timeout 1800 bash -c '
	until grep -q "FWTS tests completed" /tmp/results/screen.log 2>/dev/null; do
	    sleep 5
	    echo "Running FWTS tests"
	done'

        echo 'Shutting down QEMU...'
        screen -S qemu -X stuff 'poweroff\n'
        sleep 10
    } > /tmp/results/screen.log
else
    echo 'QEMU boot timeout'
fi

echo 'Container execution completed'
