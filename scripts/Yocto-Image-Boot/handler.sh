#!/bin/bash

# ./handler build -> ./handler run

IMAGE="core-image-minimal"
POKY_DIR="/home/user/poky"
BUILD_DIR="${POKY_DIR}/build"

init_volumes() {
    docker volume create yocto-build
    docker volume create yocto-downloads
    docker volume create yocto-sstate

    docker volume create yocto-meta-custom

    docker run --rm -v yocto-build:/mnt alpine \
        sh -c "mkdir -p /mnt/build && mkdir -p /mnt/conf && chown -R 1010:510 /mnt"
    docker run --rm -v yocto-downloads:/mnt alpine \
        sh -c "mkdir -p /mnt && chown -R 1010:510 /mnt"
    docker run --rm -v yocto-sstate:/mnt alpine \
        sh -c "mkdir -p /mnt && chown -R 1010:510 /mnt"

    docker run --rm -v yocto-meta-custom:/mnt alpine \
        sh -c "mkdir -p /mnt/conf && chown -R 1010:510 /mnt"
}

run_image() {
    docker run -it --rm \
        --entrypoint "" \
        -v yocto-build:/home/user/poky/build \
        -v yocto-downloads:/home/user/poky/downloads \
        -v yocto-sstate:/home/user/poky/sstate-cache \
        -v yocto-meta-custom:/home/user/poky/meta-custom \
        -v "$(pwd)/config.sh:/home/user/poky/build/config.sh" \
        -v "$(pwd)/tests.sh:/home/user/poky/build/tests.sh" \
        yocto-builder-image \
        sh -c "cd /home/user/poky/build && ./config.sh"
        # && ./tests.sh

    # Для сборки раскомментировать

    docker run -it --rm \
        -v yocto-build:/home/user/poky/build \
        -v yocto-downloads:/home/user/poky/downloads \
        -v yocto-sstate:/home/user/poky/sstate-cache \
        -v yocto-meta-custom:/home/user/poky/meta-custom \
        yocto-builder-image \
        sh -c "bitbake ${IMAGE}"
}

run_qemu() {
    docker run -it --rm \
        -v yocto-build:/home/user/poky/build \
        -v yocto-downloads:/home/user/poky/downloads \
        -v yocto-sstate:/home/user/poky/sstate-cache \
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
    # run_qemu
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
