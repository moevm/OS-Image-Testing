#!/bin/bash

IMAGE="core-image-minimal"

DIR=$(dirname "$(realpath "$0")")
LAYERS_PATH=$(realpath "$DIR/../../layers")

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
        -v "$LAYERS_PATH/meta-mytests":/home/user/poky/meta-mytests:ro \
        yocto-builder-image \
        bitbake ${IMAGE}
}

run_qemu() {
    docker run -it --rm \
        -v yocto-build:/home/user/poky/build \
        -v yocto-downloads:/home/user/poky/downloads \
        -v yocto-sstate:/home/user/poky/sstate-cache \
        -v "$LAYERS_PATH/meta-mytests":/home/user/poky/meta-mytests:ro \
        yocto-builder-image \
        runqemu qemux86-64 ${IMAGE} slirp nographic
}

copy_conf() {
    CONF_FILE_PATH="$1"
    
    if [ -z "$CONF_FILE_PATH" ]; then
        echo "Usage: $0 config /path/to/local.conf"
        exit 1
    fi
    
    if [ ! -f "$CONF_FILE_PATH" ]; then
        echo "Error: File '$CONF_FILE_PATH' does not exist."
        exit 1
    fi
    
    CONF_DIR=$(dirname "$CONF_FILE_PATH")
    CONF_FILE=$(basename "$CONF_FILE_PATH")
    
    echo "Copying $CONF_FILE_PATH into yocto-build volume..."

    docker run --rm \
        -v yocto-build:/mnt \
        -v "$CONF_DIR":/localconf:ro alpine \
        sh -c "\
            mkdir -p /mnt/conf && \
            cp /localconf/$CONF_FILE /mnt/conf/$CONF_FILE && \
            chown 1010:0 /mnt/conf/$CONF_FILE"

    echo "local.conf copied successfully to yocto-build volume."
}

build_tests() {
    docker run -it --rm \
        -v yocto-build:/home/user/poky/build \
        -v yocto-downloads:/home/user/poky/downloads \
        -v yocto-sstate:/home/user/poky/sstate-cache \
        -v "$LAYERS_PATH/meta-mytests":/home/user/poky/meta-mytests:ro \
        yocto-builder-image \
        /bin/bash -c "\
            source /home/user/poky/oe-init-build-env /home/user/poky/build && \
            echo 'checking layers...' && \
            if ! bitbake-layers show-layers | grep -q meta-mytests; then \
                bitbake-layers add-layer /home/user/poky/meta-mytests; \
            fi && \
            echo 'building tests layer...' && \
            bitbake tests"
}

if [ $# -eq 0 ]; then
    echo "Give argument for the script. build|run|test|config"
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

if [ $1 = "config" ]; then
    copy_conf "$2"
fi

if [ $1 = "test" ]; then
    build_tests
fi

