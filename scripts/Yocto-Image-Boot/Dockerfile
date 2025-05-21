FROM ubuntu:22.04

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        sudo \
        wget \
        git \
        locales \
        chrpath \
        cpio \
        diffstat \
        gawk \
        zstd \
        liblz4-tool \
        python3 \
        python3-pip \
        tar \
        gcc \
        make \
        bzip2 \
        file \
        g++ \
        patch 

RUN locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8

ENV USER user

WORKDIR /home/${USER}/poky

RUN useradd -rm -d /home/${USER} -s /bin/bash -g root -G sudo ${USER} -u 1010 &&\
    echo "${USER} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/${USER}

COPY --chown=${USER}:root . ./ 

RUN chmod +x ./entrypoint.sh

USER user

VOLUME /home/${USER}/poky/build

ENTRYPOINT ["./entrypoint.sh"]