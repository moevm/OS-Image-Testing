FROM python:3.14.4-slim-trixie

ARG USER
ARG GROUP
ARG LIB_NAME
ARG PYTHON_REQUIRED_LIBS

ENV PATH="/home/${USER}/.local/bin:${PATH}"
ENV USER="$USER"
ENV LIB_NAME="$LIB_NAME"

RUN apt update && \
    apt install -y \
    openssh-client \
    curl \
    sudo \
    less \
    vim \
    nano \
    iperf3 \
    supervisor \
    gettext && \
    apt-get clean && \
    rm --recursive --force /tmp/* /var/tmp/*

RUN groupadd -g 510 ${GROUP} && \
    useradd -rm -d /home/${USER} -s /bin/bash -g ${GROUP} -u 1010 -G sudo ${USER} && \
    echo "${USER} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/${USER}

USER ${USER}
WORKDIR /home/${USER}

RUN python3 -m pip install ${PYTHON_REQUIRED_LIBS} && \
    mkdir /home/${USER}/.ssh

COPY --chown=${USER}:${GROUP} src/ /home/${USER}/python
COPY --chown=${USER}:${GROUP} pyproject.toml /home/${USER}/python

RUN mkdir --parents /home/${USER}/${LIB_NAME}/conf && \
    chown ${USER}:${GROUP} --recursive /home/${USER}/${LIB_NAME}/

COPY --chown=${USER}:${GROUP} conf/supervisord.conf /home/${USER}/${LIB_NAME}/conf/supervisord.conf

RUN msgfmt --output-file \
    /home/${USER}/python/imgtests/web/locale/ru/LC_MESSAGES/django.mo \
    /home/${USER}/python/imgtests/web/locale/ru/LC_MESSAGES/django.po && \
    msgfmt --output-file \
    /home/${USER}/python/imgtests/web/locale/ru/LC_MESSAGES/djangojs.mo \
    /home/${USER}/python/imgtests/web/locale/ru/LC_MESSAGES/djangojs.po

RUN cd /home/${USER}/python && python3 -m pip install . && rm -rf /home/${USER}/python

COPY --chown=${USER}:${GROUP} scripts/entrypoint-analyzer.sh /home/${USER}/${LIB_NAME}/entrypoint-analyzer.sh

RUN chmod +x /home/${USER}/${LIB_NAME}/entrypoint-analyzer.sh

ENTRYPOINT ["/home/user/imgtests/entrypoint-analyzer.sh"]
