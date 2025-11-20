#!/bin/bash

sudo mkdir --parents ${BUILD_DIR}/build ${BUILD_DIR}/conf
sudo mkdir --parents ${POKY_DIR}/downloads
sudo mkdir --parents ${POKY_DIR}/sstate-cache
sudo chown --recursive ${USER}:${GROUP} ${BUILD_DIR} ${POKY_DIR}/downloads ${POKY_DIR}/sstate-cache

sudo service ssh start

# shellcheck disable=SC1091
source "/home/user/poky/oe-init-build-env" "/home/user/poky/build"
exec "$@"
