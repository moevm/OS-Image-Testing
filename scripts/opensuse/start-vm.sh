#!/bin/bash

set -e

cd "${SUSE_DIR}"

echo "Waiting for OpenSUSE image to be ready..."
while true; do
    for img in open-suse-*.ready.qcow2; do
        [ -f "$img" ] && IMAGE="$img" && break 2
    done
    sleep 10
done

exec qemu-system-x86_64 -enable-kvm -m "${VM_RAM}" -smp "${CPUS}" -nographic \
    -monitor tcp:0.0.0.0:4444,server,nowait \
    -drive file="$IMAGE",index=0,media=disk \
    -cdrom cloud-init.iso \
    -net user,hostfwd=tcp::"${SSH_SUSE_PORT}"-:"${SSH_QEMU_PORT}",hostfwd=tcp::"${SUSE_NE_PORT}"-:"${DEFAULT_NE_PORT}",hostfwd=tcp:0.0.0.0:"${IPERF3_PORT}"-:"${IPERF3_PORT}",hostfwd=udp:0.0.0.0:"${IPERF3_PORT}"-:"${IPERF3_PORT}" \
    -net nic
