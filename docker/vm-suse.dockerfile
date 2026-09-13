FROM ubuntu:24.04

ARG USER

ENV DEBIAN_FRONTEND=noninteractive \
    SUSE_DIR=/home/${USER}/suse

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    qemu-system \
    qemu-utils \
    qemu-user-static

WORKDIR ${SUSE_DIR}

COPY scripts/opensuse/start-vm.sh /start-vm.sh
RUN chmod +x /start-vm.sh

ENTRYPOINT ["/start-vm.sh"]
