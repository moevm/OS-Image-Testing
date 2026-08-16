#!/bin/bash

set -e

./scripts/download_images.py "$1"
./scripts/cloud-setup.sh "${S_USER}" "${PASSWORD}"
CPUS=4
qemu-system-x86_64 -m "${VM_RAM}" -smp "${CPUS}" -nographic -monitor tcp:0.0.0.0:4444,server,nowait -drive file=open-suse-"$1".ready.qcow2,index=0,media=disk \
				   -cdrom cloud-init.iso -net user,hostfwd=tcp::"${SSH_SUSE_PORT}"-:"${SSH_QEMU_PORT}",hostfwd=tcp::"${SUSE_NE_PORT}"-:"${DEFAULT_NE_PORT}",hostfwd=tcp:0.0.0.0:"${IPERF3_PORT}"-:"${IPERF3_PORT}",hostfwd=udp:0.0.0.0:"${IPERF3_PORT}"-:"${IPERF3_PORT}" -net nic
