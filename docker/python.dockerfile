FROM python:3.13.11-slim-trixie

ARG USER
ARG GROUP

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

ENV PATH="/home/${USER}/.local/bin:${PATH}"
ENV MPLBACKEND=Agg

RUN mkdir /home/${USER}/.ssh

COPY --chown=${USER}:${GROUP} src/ /home/${USER}/python
COPY --chown=${USER}:${GROUP} pyproject.toml /home/${USER}/python
RUN cd /home/${USER}/python && \
    python3 -m pip install --user -U pip setuptools wheel && \
    python3 -m pip install --user . && \
    python3 -m pip install --user fio-plot matplotlib
RUN rm -rf /home/${USER}/python

VOLUME [ "/home/${USER}/tests" ]
