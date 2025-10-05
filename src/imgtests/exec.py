from pathlib import Path
import subprocess
import logging
from typing import NamedTuple

import paramiko


logger = logging.getLogger(__name__)


class ExecResult(NamedTuple):
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0


def run_command(cmd: list[str]) -> ExecResult:
    logger.info("Running command %s", " ".join(cmd))
    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8", check=False
    )

    return ExecResult(
        stdout=result.stdout,
        stderr=result.stderr,
        returncode=result.returncode,
    )


class SSHClient:
    def __init__(
        self, hostname: str, username: str = "root", password: str | None = None, port: int = 22
    ) -> None:
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port
        self.ssh_session = paramiko.Transport((self.hostname, self.port))
        logger.info("Connecting to the host '%s'.", self.hostname)
        self.ssh_session.connect(username=self.username, password=self.password)

    def __call__(
        self,
        cmd: str,
    ) -> ExecResult:
        session = self.ssh_session.open_channel(kind="session")
        std = session.makefile("rb", -1)
        logger.info("Running command '%s' on host '%s'.", cmd, self.hostname)
        session.exec_command(cmd)
        stdout = std.read().decode("utf-8")
        retval = session.recv_exit_status()
        logger.info(f"Exit status: {retval}.")
        if retval:
            logger.error(f"Command '{cmd.strip()}' completed with errors.")
        session.close()
        return ExecResult(stdout=stdout, returncode=retval)

    def close(self) -> None:
        self.ssh_session.close()

    def reconnect(self) -> None:
        self.close()
        self.ssh_session = paramiko.Transport((self.hostname, self.port))
        logger.info("Connecting to the host '%s'.", self.hostname)
        self.ssh_session.connect(username=self.username, password=self.password)

    def upload(self, localpath: Path, remotepath: Path) -> ExecResult:
        sftp = paramiko.SFTPClient.from_transport(self.ssh_session)
        if sftp is None:
            logger.error("Can't open channel for upload file via sftp.")
            return ExecResult(returncode=1)
        logger.info("Copy '%s' to the remote path '%s'.", localpath, remotepath)
        sftp.put(localpath, str(remotepath))
        sftp.close()
        return ExecResult()

    def download(self, remotepath: Path, localpath: Path) -> ExecResult:
        sftp = paramiko.SFTPClient.from_transport(self.ssh_session)
        if sftp is None:
            logger.error("Can't open channel for upload file via sftp.")
            return ExecResult(returncode=1)
        logger.info("Copy '%s' to the local path '%s'.", remotepath, localpath)
        sftp.get(str(remotepath), localpath)
        sftp.close()
        return ExecResult()
