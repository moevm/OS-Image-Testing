#!/bin/bash

set -e

./scripts/download_images.py "$1"
./scripts/cloud-setup.sh "${S_USER}" "${PASSWORD}"
qemu-system-x86_64 -m 4G -nographic -drive file=open-suse-"$1".ready.qcow2,index=0,media=disk \
				   -cdrom cloud-init.iso -net user,hostfwd=tcp::"${SSH_SUSE_PORT}"-:"${SSH_QEMU_PORT}",hostfwd=tcp::"${SUSE_NE_PORT}"-:"${DEFAULT_NE_PORT}" -net nic
