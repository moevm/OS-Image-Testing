#!/bin/bash

IMAGE="core-image-minimal"

init_volumes() {
    docker volume create yocto-build
    docker volume create yocto-downloads
    docker volume create yocto-sstate

    docker run --rm -v yocto-build:/mnt alpine \
        sh -c "mkdir -p /mnt/{build,conf} && chown -R 1010:0 /mnt"
    docker run --rm -v yocto-downloads:/mnt alpine \
        sh -c "mkdir -p /mnt && chown -R 1010:0 /mnt"
    docker run --rm -v yocto-sstate:/mnt alpine \
        sh -c "mkdir -p /mnt && chown -R 1010:0 /mnt"
}

run_image() {
    docker run -it --rm \
        -v yocto-build:/home/user/poky/build \
        -v yocto-downloads:/home/user/poky/downloads \
        -v yocto-sstate:/home/user/poky/sstate-cache \
        yocto-builder-image \
        bitbake ${IMAGE}
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
    run_qemu
fi

if [ $1 = "test" ]; then
    exit
fi
