FROM ubuntu:22.04

ARG USER
ARG GROUP

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=en_US.UTF-8 \
    POKY_DIR=/home/${USER}/poky

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        sudo wget git locales chrpath cpio diffstat gawk \
        zstd liblz4-tool python3 python3-pip tar gcc make \
        bzip2 file g++ patch python3-pexpect python3-git \
        python3-jinja2 python3-subunit screen \
        libtirpc-dev libtirpc3 pkg-config \
        qemu qemu-system-x86 qemu-utils && \
    rm -rf /var/lib/apt/lists/* && \
    locale-gen en_US.UTF-8

RUN mkdir -p ${POKY_DIR} && \
    git clone --depth 1 -b scarthgap --recurse-submodules https://git.yoctoproject.org/poky ${POKY_DIR}

RUN groupadd -g 510 ${GROUP} && \
    useradd -rm -d /home/${USER} -s /bin/bash -g {GROUP} -u 1010 -G sudo ${USER} && \
    echo "${USER} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/${USER} && \
    chown -R ${USER}:{GROUP} ${POKY_DIR}

COPY scripts/Yocto-Image-Boot/entrypoint.sh ${POKY_DIR}/
RUN chmod +x ${POKY_DIR}/entrypoint.sh

USER ${USER}
WORKDIR ${POKY_DIR}

ENTRYPOINT ["/home/user/poky/entrypoint.sh"]
CMD ["/bin/bash"]
