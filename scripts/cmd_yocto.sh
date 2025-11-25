#!/bin/bash

set -e

cd "${POKY_DIR}"
./add-layers.sh
bitbake "${OS_IMAGE}"
QB_SLIRP_OPT="-netdev user,id=net0,hostfwd=tcp::8080-:80,hostfwd=tcp::2222-:22" \
    runqemu qemux86-64 slirp nographic
