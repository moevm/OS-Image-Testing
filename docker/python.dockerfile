FROM python:3.13.12-slim-trixie

ARG USER
ARG GROUP

ENV PATH="/home/${USER}/.local/bin:${PATH}"

RUN apt update && \
    apt install -y \
    openssh-client \
    curl \
    sudo

RUN groupadd -g 510 ${GROUP} && \
    useradd -rm -d /home/${USER} -s /bin/bash -g ${GROUP} -u 1010 -G sudo ${USER} && \
    echo "${USER} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/${USER}

USER ${USER}
WORKDIR /home/${USER}

RUN mkdir /home/${USER}/.ssh

COPY --chown=${USER}:${GROUP} src/ /home/${USER}/python
COPY --chown=${USER}:${GROUP} pyproject.toml /home/${USER}/python
RUN cd /home/${USER}/python && python3 -m pip install .
RUN rm -rf /home/${USER}/python

VOLUME [ "/home/${USER}/tests" ]
