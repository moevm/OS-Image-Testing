#!/bin/bash

rm -rf /home/user/poky/meta-openjdk-temurin/recipes-java/helloworld-java

# shellcheck disable=SC1091
source "/home/user/poky/oe-init-build-env" "/home/user/poky/build"

ROOTFS_IMAGE="${POKY_DIR}/build/tmp/deploy/images/qemux86-64/${OS_IMAGE}-qemux86-64.rootfs.ext4.qcow2"

QB_SLIRP_OPT="-netdev user,id=net0,hostfwd=tcp::8080-:80,hostfwd=tcp::${SSH_QEMU_PORT}-:${SSH_TO_QEMU_PORT},hostfwd=tcp::${YOCTO_NE_PORT}-:${DEFAULT_NE_PORT},hostfwd=tcp:0.0.0.0:${IPERF3_PORT}-:${IPERF3_PORT},hostfwd=udp:0.0.0.0:${IPERF3_PORT}-:${IPERF3_PORT}" \
    runqemu qemux86-64 kvm slirp nographic "${ROOTFS_IMAGE}" qemuparams="-monitor tcp:0.0.0.0:4444,server,nowait -smp ${CPUS}"
