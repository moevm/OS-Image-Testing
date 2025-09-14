#!/bin/bash

OPTS=$(getopt -o brt --long build,run,test -n 'handler.sh' -- "$@")

IMAGE="core-image-minimal"
USER="user"
GROUP="yoctogroup"

POKY_DIR="/home/${USER}/poky"
BUILD_DIR="${POKY_DIR}/build"
LAYER_DIR="${POKY_DIR}/meta-custom"

HOST_DIR=$(dirname "$(realpath "$0")")
HOST_LAYERS_PATH=$(realpath "$HOST_DIR/../../layers")
HOST_CONF_PATH=$(realpath "$HOST_DIR/../../conf")

init_volumes() {
    docker volume create yocto-build
    docker volume create yocto-downloads
    docker volume create yocto-sstate
    docker volume create yocto-meta-custom

    docker run --rm --user root \
        --entrypoint "" \
        -v yocto-build:/tmp-build \
        -v yocto-downloads:/tmp-downloads \
        -v yocto-sstate:/tmp-sstate \
        -v yocto-meta-custom:/tmp-meta-custom \
        yocto-builder-image \
        bash -c "mkdir -p /tmp-build/build /tmp-build/conf &&
            mkdir -p /tmp-downloads &&
            mkdir -p /tmp-sstate &&
            mkdir -p /tmp-meta-custom/conf &&
            chown -R ${USER}:${GROUP} /tmp-build /tmp-downloads /tmp-sstate /tmp-meta-custom"
}

run_image() {
    docker run -it --rm \
        -v yocto-build:${BUILD_DIR} \
        -v yocto-downloads:${POKY_DIR}/downloads \
        -v yocto-sstate:${POKY_DIR}/sstate-cache \
        -v yocto-meta-custom:${LAYER_DIR} \
        -v "${HOST_CONF_PATH}/local.conf:${BUILD_DIR}/conf/local.conf" \
        -v "${HOST_LAYERS_PATH}/meta-custom/conf/layer.conf:${LAYER_DIR}/conf/layer.conf" \
        -v "${HOST_LAYERS_PATH}/meta-custom/recipes-stress/stress-ng/stress-ng_1.0.0.bb:${LAYER_DIR}/recipes-stress/stress-ng/stress-ng_1.0.0.bb" \
        -v "${HOST_LAYERS_PATH}/meta-custom/recipes-stress/stress-ng/files:${LAYER_DIR}/recipes-stress/stress-ng/files" \
        yocto-builder-image \
        bash -c "bitbake-layers add-layer ${LAYER_DIR} && bitbake ${IMAGE}"
}

run_qemu() {
    docker run -it --rm \
        -v yocto-build:${BUILD_DIR} \
        -v yocto-downloads:${POKY_DIR}/downloads \
        -v yocto-sstate:${POKY_DIR}/sstate-cache \
        -v yocto-meta-custom:${LAYER_DIR} \
        -v "${HOST_CONF_PATH}/local.conf:${BUILD_DIR}/conf/local.conf" \
        -v "${HOST_LAYERS_PATH}/meta-custom/conf/layer.conf:${LAYER_DIR}/conf/layer.conf" \
        -v "${HOST_LAYERS_PATH}/meta-custom/recipes-stress/stress-ng/stress-ng_1.0.0.bb:${LAYER_DIR}/recipes-stress/stress-ng/stress-ng_1.0.0.bb" \
        -v "${HOST_LAYERS_PATH}/meta-custom/recipes-stress/stress-ng/files:${LAYER_DIR}/recipes-stress/stress-ng/files" \
        yocto-builder-image \
        runqemu --config /home/${USER}/poky/build/tmp/deploy/images/qemux86-64/core-image-minimal-qemux86-64.rootfs.qemuboot.conf slirp nographic
}

while [ $# -ne 0 ]; do
    case "$1" in
        -b | --build)
            docker build -t yocto-builder-image .
            init_volumes
            shift
            ;;
        -r | --run)
            run_image
            run_qemu
            shift
            ;;
        --)
            shift
            ;;
        *)
            echo "Unknown argument!"
            exit 1
            ;;
    esac
done
