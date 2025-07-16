#!/bin/bash

set -euo pipefail

SSH_PORT=2222
SSH_USER="root"
SSH_HOST="localhost"
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"

usage() {
    echo "Usage:"
    echo "  $0 --prepare /path/to/tests-dir   # Prepare tests by copying to VM"
    echo "  $0                                # Run tests from tests/ folder on VM"
    exit 1
}

wait_for_ssh() {
    echo "Waiting for SSH to become available on $SSH_HOST:$SSH_PORT..."
    until ssh $SSH_OPTS -p $SSH_PORT $SSH_USER@$SSH_HOST echo "SSH ready" &>/dev/null; do
        sleep 1
    done
    echo "SSH is available."
}

prepare_tests() {
    local src_dir="$1"
    if [[ ! -d "$src_dir" ]]; then
        echo "Error: Tests directory '$src_dir' not found."
        exit 2
    fi

    wait_for_ssh

    echo "Clearing /root/tests directory on VM..."
    ssh $SSH_OPTS -p $SSH_PORT $SSH_USER@$SSH_HOST "rm -rf /root/tests && mkdir -p /root/tests"

    echo "Copying tests from '$src_dir' to /root/tests on VM..."
    scp $SSH_OPTS -P $SSH_PORT -r "$src_dir"/* $SSH_USER@$SSH_HOST:/root/tests/
    ssh $SSH_OPTS -p $SSH_PORT $SSH_USER@$SSH_HOST "chmod +x /root/tests/*"

    echo "Test preparation completed."
}

run_tests() {
    wait_for_ssh

    echo "Running tests from /root/tests on VM..."


    scripts=$(ssh $SSH_OPTS -p $SSH_PORT $SSH_USER@$SSH_HOST "find /root/tests -maxdepth 1 -type f -executable" || true)

    if [[ -z "$scripts" ]]; then
        echo "No executable test scripts found in /root/tests"
        exit 3
    fi

    for script in $scripts; do
        echo "Running test: $script"
        ssh $SSH_OPTS -p $SSH_PORT $SSH_USER@$SSH_HOST "$script"
        echo "-----------------------------"
    done

    echo "All tests completed."
}

if [[ $# -eq 2 && "$1" == "--prepare" ]]; then
    prepare_tests "$2"
elif [[ $# -eq 0 ]]; then
    run_tests
else
    usage
fi