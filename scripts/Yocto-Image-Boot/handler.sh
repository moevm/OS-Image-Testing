#!/bin/bash

OPTS=$(getopt -o brt --long build,run,test -n 'handler.sh' -- "$@")

IMAGE="core-image-minimal"
USER="1010"
GROUP="510"

POKY_DIR="/home/user/poky"
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
        -v "${HOST_LAYERS_PATH}/meta-custom/recipes-login/auto-login/auto-login_1.0.0.bb:${LAYER_DIR}/recipes-login/auto-login/auto-login_1.0.0.bb" \
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
        -v "${HOST_LAYERS_PATH}/meta-custom/recipes-login/auto-login/auto-login_1.0.0.bb:${LAYER_DIR}/recipes-login/auto-login/auto-login_1.0.0.bb" \
        yocto-builder-image \
        runqemu --config /home/user/poky/build/tmp/deploy/images/qemux86-64/core-image-minimal-qemux86-64.rootfs.qemuboot.conf slirp nographic
}

test_qemu() {
    local temp_dir=$(mktemp -d)
    chmod 777 "$temp_dir"
    local log_file="$temp_dir/test.log"

    docker run --rm \
        -v yocto-build:${BUILD_DIR} \
        -v yocto-downloads:${POKY_DIR}/downloads \
        -v yocto-sstate:${POKY_DIR}/sstate-cache \
        -v yocto-meta-custom:${LAYER_DIR} \
        -v "${HOST_CONF_PATH}/local.conf:${BUILD_DIR}/conf/local.conf" \
        -v "${HOST_LAYERS_PATH}/meta-custom/conf/layer.conf:${LAYER_DIR}/conf/layer.conf" \
        -v "${HOST_LAYERS_PATH}/meta-custom/recipes-stress/stress-ng/stress-ng_1.0.0.bb:${LAYER_DIR}/recipes-stress/stress-ng/stress-ng_1.0.0.bb" \
        -v "${HOST_LAYERS_PATH}/meta-custom/recipes-stress/stress-ng/files:${LAYER_DIR}/recipes-stress/stress-ng/files" \
        -v "${HOST_LAYERS_PATH}/meta-custom/recipes-login/auto-login/auto-login_1.0.0.bb:${LAYER_DIR}/recipes-login/auto-login/auto-login_1.0.0.bb" \
        -v "$temp_dir:/tmp/results" \
        yocto-builder-image \
        bash -c "
            screen -L -Logfile /tmp/results/screen.log -h 10000 -dmS qemu runqemu --config /home/user/poky/build/tmp/deploy/images/qemux86-64/core-image-minimal-qemux86-64.rootfs.qemuboot.conf slirp nographic
            
            # Время для запуска QEMU
            timeout 60 bash -c '
                while ! grep -q \"login:\" /tmp/results/screen.log 2>/dev/null; do
                    sleep 2
                done
            '
    
            > /tmp/results/screen.log

            # Запуск раннера
            screen -S qemu -X stuff 'ptest-runner stress-ng\n'

            # Время для тестов
            timeout 300 bash -c '
                while ! grep -q \"STOP: ptest-runner\" /tmp/results/screen.log 2>/dev/null; do
                    sleep 2
                done
            '
            
            # Выключение и ожидание завершения QEMU
            screen -S qemu -X stuff 'poweroff\n'
            sleep 10
        
            # Перенос логов
            cat /tmp/results/screen.log > /tmp/results/test.log
        "
    
    cat "$log_file"
    
    rm -rf "$temp_dir"
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
        -t | --test)
            run_image
            test_qemu
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
