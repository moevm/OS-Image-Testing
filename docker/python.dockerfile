FROM python:3.13.7-slim-trixie

ARG USER
ARG GROUP

RUN apt update && \
    apt install -y \
    python3-paramiko \
    python3-alembic \
    python3-scp \
    python3-flask-sqlalchemy \
    openssh-server \
    sudo

RUN mkdir -p /home/${USER}/results
RUN mkdir /home/${USER}/scripts
RUN groupadd -g 510 ${GROUP} && \
    useradd -rm -d /home/${USER} -s /bin/bash -g ${GROUP} -u 1010 -G sudo ${USER} && \
    echo "${USER} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/${USER} && \
    chown -R ${USER}:${GROUP} /home/${USER}/results && \
    chown -R ${USER}:${GROUP} /home/${USER}/scripts

RUN mkdir /home/${USER}/.ssh

COPY scripts/entrypoint_analyzer.sh /home/${USER}/scripts/
RUN chmod +x /home/${USER}/scripts/entrypoint_analyzer.sh

COPY ../scripts/wait_for_results.sh /home/${USER}/scripts/
RUN chmod +x /home/${USER}/scripts/wait_for_results.sh

ENTRYPOINT ["/home/user/scripts/entrypoint_analyzer.sh"]

CMD ["/home/user/scripts/wait_for_results.sh"]
