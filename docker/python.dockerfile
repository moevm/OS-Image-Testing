FROM python:3.13.7-slim-trixie

ARG USER
ARG GROUP
ARG PASSWORD

ENV SSH_USER=${USER}
ENV SSH_PASSWORD=${PASSWORD}

RUN apt update && \
    apt install -y \
    openssh-client \
    sudo

RUN mkdir -p /home/${USER}/results
RUN mkdir /home/${USER}/scripts
RUN groupadd -g 510 ${GROUP} && \
    useradd -rm -d /home/${USER} -s /bin/bash -g ${GROUP} -u 1010 -G sudo ${USER} && \
    echo "${USER} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/${USER} && \
    chown -R ${USER}:${GROUP} /home/${USER}/results && \
    chown -R ${USER}:${GROUP} /home/${USER}/scripts

RUN mkdir /home/${USER}/.ssh

COPY src/ /home/${USER}/python
COPY pyproject.toml /home/${USER}/python
WORKDIR /home/${USER}/python
RUN python3 -m pip install .

COPY scripts/get-remote-results.py /home/user/

ENTRYPOINT ["/home/user/scripts/entrypoint_analyzer.sh"]
