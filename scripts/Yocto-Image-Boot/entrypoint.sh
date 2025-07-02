#!/bin/bash

POKY_DIR="/home/user/poky"
BUILD_DIR="${POKY_DIR}/build"

sudo chown -R user:root ${POKY_DIR}/{build,downloads,sstate-cache}
chmod -R 775 ${POKY_DIR}/{build,downloads,sstate-cache}

if [ ! -f "${BUILD_DIR}/conf/local.conf" ]; then
    mkdir -p "${BUILD_DIR}/conf"
    source "${POKY_DIR}/oe-init-build-env" "${BUILD_DIR}"
    
    sed -i "s|#DL_DIR ?= \"|DL_DIR ?= \"${POKY_DIR}/downloads|" ${BUILD_DIR}/conf/local.conf
    sed -i "s|#SSTATE_DIR ?= \"|SSTATE_DIR ?= \"${POKY_DIR}/sstate-cache|" ${BUILD_DIR}/conf/local.conf
    echo "BB_NUMBER_THREADS = \"$(nproc)\"" >> ${BUILD_DIR}/conf/local.conf
    echo "PARALLEL_MAKE = \"-j $(nproc)\"" >> ${BUILD_DIR}/conf/local.conf
fi

source "${POKY_DIR}/oe-init-build-env" "${BUILD_DIR}"
exec "$@"