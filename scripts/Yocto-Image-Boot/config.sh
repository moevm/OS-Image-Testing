#!/bin/bash

POKY_DIR="/home/user/poky"
BUILD_DIR="${POKY_DIR}/build"

mkdir -p "${BUILD_DIR}/conf"

# rm ${BUILD_DIR}/conf/local.conf # убрать

source "${POKY_DIR}/oe-init-build-env" "${BUILD_DIR}"

sed -i "s|#DL_DIR ?= \"|DL_DIR ?= \"${POKY_DIR}/downloads|" ${BUILD_DIR}/conf/local.conf
sed -i "s|#SSTATE_DIR ?= \"|SSTATE_DIR ?= \"${POKY_DIR}/sstate-cache|" ${BUILD_DIR}/conf/local.conf

echo "DISTRO_FEATURES:append = \" ptest\"" >> ${BUILD_DIR}/conf/local.conf

echo "IMAGE_INSTALL:append = \" stress-ng wget\"" >> ${BUILD_DIR}/conf/local.conf

echo "EXTRA_IMAGE_FEATURES += \"ptest-pkgs\"" >> ${BUILD_DIR}/conf/local.conf
echo "PTEST_ENABLED = \"1\"" >> ${BUILD_DIR}/conf/local.conf

echo "BB_NUMBER_THREADS = \"$(nproc)\"" >> ${BUILD_DIR}/conf/local.conf
echo "PARALLEL_MAKE = \"-j $(nproc)\"" >> ${BUILD_DIR}/conf/local.conf
