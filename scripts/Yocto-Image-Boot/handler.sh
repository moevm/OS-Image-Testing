#!/bin/bash

# ./handler build -> ./handler run

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
        --entrypoint "" \
        -v yocto-build:${BUILD_DIR} \
        -v yocto-downloads:${POKY_DIR}/downloads \
        -v yocto-sstate:${POKY_DIR}/sstate-cache \
        -v yocto-meta-custom:${LAYER_DIR} \
        -v "$(pwd)/local.conf:${BUILD_DIR}/conf/local.conf" \
        -v "$(pwd)/layer.conf:${LAYER_DIR}/conf/layer.conf" \
        -v "$(pwd)/stress-ng_1.0.0.bb:${LAYER_DIR}/recipes-stress/stress-ng_1.0.0.bb" \
        yocto-builder-image \
        bash -c "source ${POKY_DIR}/oe-init-build-env ${BUILD_DIR} && bitbake-layers add-layer ${LAYER_DIR}"

    docker run -it --rm \
        -v yocto-build:${BUILD_DIR} \
        -v yocto-downloads:${POKY_DIR}/downloads \
        -v yocto-sstate:${POKY_DIR}/sstate-cache \
        -v yocto-meta-custom:${LAYER_DIR} \
        -v "$(pwd)/local.conf:${BUILD_DIR}/conf/local.conf" \
        -v "$(pwd)/layer.conf:${LAYER_DIR}/conf/layer.conf" \
        -v "$(pwd)/stress-ng_1.0.0.bb:${LAYER_DIR}/recipes-stress/stress-ng_1.0.0.bb" \
        yocto-builder-image \
        sh -c "bitbake ${IMAGE}"
}

run_qemu() {
    docker run -it --rm \
        -v yocto-build:${BUILD_DIR} \
        -v yocto-downloads:${POKY_DIR}/downloads \
        -v yocto-sstate:${POKY_DIR}/sstate-cache \
        -v yocto-meta-custom:${LAYER_DIR} \
        -v "$(pwd)/local.conf:${BUILD_DIR}/conf/local.conf" \
        -v "$(pwd)/layer.conf:${LAYER_DIR}/conf/layer.conf" \
        -v "$(pwd)/stress-ng_1.0.0.bb:${LAYER_DIR}/recipes-stress/stress-ng_1.0.0.bb" \
        yocto-builder-image \
        runqemu qemux86-64 ${IMAGE} slirp nographic
}

if [ $# -eq 0 ]; then
    echo "Give argument for the script. build|run|test"
    exit
fi

if [ $1 = "build" ]; then
    init_volumes
    docker build -t yocto-builder-image .
fi

if [ $1 = "run" ]; then
    run_image
    run_qemu
fi

# if [ $1 = "test" ]; then
#     docker run -it --rm \
#         -v yocto-build:/home/user/poky/build \
#         -v yocto-downloads:/home/user/poky/downloads \
#         -v yocto-sstate:/home/user/poky/sstate-cache \
#         yocto-builder-image \
#         bitbake-layers show-recipes stress-ng
    
#     docker run -it --rm \
#         -v yocto-build:/home/user/poky/build \
#         -v yocto-downloads:/home/user/poky/downloads \
#         -v yocto-sstate:/home/user/poky/sstate-cache \
#         yocto-builder-image \
#         grep -r "inherit ptest" $(find . -name "*stress-ng*.bb")
# fi
