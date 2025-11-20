#!/bin/bash

set -e

cd "${POKY_DIR}"
./add-layers.sh
bitbake "${OS_IMAGE}"
runqemu qemux86-64 slirp nographic
