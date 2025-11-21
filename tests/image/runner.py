import logging
import os
from pathlib import Path
from time import sleep
from typing import Final

import paramiko
import paramiko.ssh_exception

from imgtests.exec.exec import SSHClient
from imgtests.logger import set_handlers

SSH_PASSWORD: Final = os.environ.get("SSH_PASS")
SSH_USER: Final = os.environ.get("SSH_USER")
SSH_ADDR: Final = os.environ.get("SSH_ADDR")

logger = logging.getLogger(__name__)
set_handlers(logger, Path("processing.log"))


def wait_remote() -> SSHClient | None:
    wait_sec = 60 * 60 * 5
    step_sec = 60
    while wait_sec > 0:
        try:
            return SSHClient(SSH_ADDR, SSH_USER, SSH_PASSWORD, 2222)
        except paramiko.ssh_exception.SSHException:
            logger.info("Waiting remote node to build image.")
        sleep(step_sec)
        wait_sec -= 60
    return None


if __name__ == "__main__":
    client = wait_remote()
