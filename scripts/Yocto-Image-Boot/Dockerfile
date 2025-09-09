FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=en_US.UTF-8 \
    USER=user \
    POKY_DIR=/home/user/poky

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        sudo wget git locales chrpath cpio diffstat gawk \
        zstd liblz4-tool python3 python3-pip tar gcc make \
        bzip2 file g++ patch python3-pexpect python3-git \
        python3-jinja2 python3-subunit screen \
        qemu qemu-system-x86 qemu-utils && \
    rm -rf /var/lib/apt/lists/* && \
    locale-gen en_US.UTF-8

RUN mkdir -p ${POKY_DIR} && \
    git clone --depth 1 -b kirkstone --recurse-submodules https://git.yoctoproject.org/poky ${POKY_DIR}

RUN groupadd -g 510 yoctogroup && \
    useradd -rm -d /home/${USER} -s /bin/bash -g yoctogroup -u 1010 -G sudo ${USER} && \
    echo "${USER} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/${USER} && \
    chown -R ${USER}:yoctogroup ${POKY_DIR}

COPY entrypoint.sh ${POKY_DIR}/
RUN chmod +x ${POKY_DIR}/entrypoint.sh

USER ${USER}
WORKDIR ${POKY_DIR}

ENTRYPOINT ["/home/user/poky/entrypoint.sh"]
CMD ["/bin/bash"]