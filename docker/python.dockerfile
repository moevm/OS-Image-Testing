FROM python:3.13.7-slim-trixie

RUN apt update && \
    apt install -y \
    python3-paramiko \
    python3-alembic \
    python3-scp \
    python3-flask-sqlalchemy \
    openssh-client

RUN ssh-keygen -t rsa -f /root/.ssh/id_rsa -N ""

CMD ["/bin/bash"]
