#!/bin/bash

OPTS=$(getopt -o br --long build,run -n 'handler.sh' -- "$@")

IMAGE="core-image-minimal"
POKY_DIR="/home/user/poky"
BUILD_DIR="${POKY_DIR}/build"
LAYER_DIR="${POKY_DIR}/meta-custom"

init_volumes() {
    docker volume create yocto-build
    docker volume create yocto-downloads
    docker volume create yocto-sstate
    docker volume create yocto-meta-custom

    docker run --rm \
        -v yocto-build:/tmp-build \
        -v yocto-downloads:/tmp-downloads \
        -v yocto-sstate:/tmp-sstate \
        -v yocto-meta-custom:/tmp-meta-custom \
        alpine \
        sh -c "mkdir -p /tmp-build/build /tmp-build/conf &&
            mkdir -p /tmp-downloads &&
            mkdir -p /tmp-sstate &&
            mkdir -p /tmp-meta-custom/conf &&
            chown -R 1010:510 /tmp-build /tmp-downloads /tmp-sstate /tmp-meta-custom"
}

run_image() {
    docker run -it --rm \
        -v yocto-build:${BUILD_DIR} \
        -v yocto-downloads:${POKY_DIR}/downloads \
        -v yocto-sstate:${POKY_DIR}/sstate-cache \
        -v yocto-meta-custom:${LAYER_DIR} \
        -v "$(pwd)/conf/local.conf:${BUILD_DIR}/conf/local.conf" \
        -v "$(pwd)/conf/layer.conf:${LAYER_DIR}/conf/layer.conf" \
        -v "$(pwd)/stress-ng_1.0.0.bb:${LAYER_DIR}/recipes-stress/stress-ng_1.0.0.bb" \
        -v "$(pwd)/tests:${LAYER_DIR}/recipes-stress/files" \
        yocto-builder-image \
        bash -c "bitbake-layers add-layer ${LAYER_DIR} && bitbake ${IMAGE}"
}

run_qemu() {
    docker run -it --rm \
        -v yocto-build:${BUILD_DIR} \
        -v yocto-downloads:${POKY_DIR}/downloads \
        -v yocto-sstate:${POKY_DIR}/sstate-cache \
        -v yocto-meta-custom:${LAYER_DIR} \
        -v "$(pwd)/conf/local.conf:${BUILD_DIR}/conf/local.conf" \
        -v "$(pwd)/conf/layer.conf:${LAYER_DIR}/conf/layer.conf" \
        -v "$(pwd)/stress-ng_1.0.0.bb:${LAYER_DIR}/recipes-stress/stress-ng_1.0.0.bb" \
        -v "$(pwd)/tests:${LAYER_DIR}/recipes-stress/files" \
        yocto-builder-image \
        runqemu qemux86-64 ${IMAGE} slirp nographic
}

while [ $# -ne 0 ]; do
    case "$1" in
        -b | --build)
            init_volumes
            docker build -t yocto-builder-image .
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
