#!/bin/bash

OPTS=$(getopt -o brt --long build,run,test -n 'handler.sh' -- "$@")

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
        -v "$(pwd)/auto-login_1.0.0.bb:${LAYER_DIR}/recipes-login/stress/auto-login_1.0.0.bb}" \
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
        -v "$(pwd)/auto-login_1.0.0.bb:${LAYER_DIR}/recipes-login/stress/auto-login_1.0.0.bb}" \
        -v "$(pwd)/tests:${LAYER_DIR}/recipes-stress/files" \
        yocto-builder-image \
        runqemu qemux86-64 ${IMAGE} slirp nographic
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
        -v "$(pwd)/conf/local.conf:${BUILD_DIR}/conf/local.conf" \
        -v "$(pwd)/conf/layer.conf:${LAYER_DIR}/conf/layer.conf" \
        -v "$(pwd)/stress-ng_1.0.0.bb:${LAYER_DIR}/recipes-stress/stress-ng_1.0.0.bb" \
        -v "$(pwd)/auto-login_1.0.0.bb:${LAYER_DIR}/recipes-login/stress/auto-login_1.0.0.bb}" \
        -v "$(pwd)/tests:${LAYER_DIR}/recipes-stress/files" \
        -v "$temp_dir:/tmp/results" \
        yocto-builder-image \
        bash -c "
            screen -L -Logfile /tmp/results/screen.log -h 10000 -dmS qemu runqemu qemux86-64 ${IMAGE} slirp nographic
            
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
            init_volumes
            docker build -t yocto-builder-image .
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
