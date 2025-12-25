FROM ubuntu:24.04

ARG USER

ENV DEBIAN_FRONTEND=noninteractive \
    SUSE_DIR=/home/${USER}/suse

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    qemu-system \
    qemu-utils \
    qemu-user-static \
    cloud-init \
    cloud-image-utils \
    wget \
    python3-pip

RUN pip3 install requests~=2.32.5 beautifulsoup4~=4.14.3 --break-system-packages

WORKDIR ${SUSE_DIR}

CMD ["/bin/bash"]
