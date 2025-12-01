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
    wget

WORKDIR ${SUSE_DIR}
CMD ["/bin/bash"]
