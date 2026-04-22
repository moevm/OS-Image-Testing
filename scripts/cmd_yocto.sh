#!/bin/bash

set -e

cd "${POKY_DIR}"
./add-layers.sh
bitbake "${OS_IMAGE}"
QB_SLIRP_OPT="-netdev user,id=net0,hostfwd=tcp::8080-:80,hostfwd=tcp::${SSH_QEMU_PORT}-:${SSH_TO_QEMU_PORT},hostfwd=tcp::${YOCTO_NE_PORT}-:${DEFAULT_NE_PORT},hostfwd=tcp:0.0.0.0:${IPERF3_PORT}-:${IPERF3_PORT},hostfwd=udp:0.0.0.0:${IPERF3_PORT}-:${IPERF3_PORT}" \
    runqemu qemux86-64 slirp nographic
