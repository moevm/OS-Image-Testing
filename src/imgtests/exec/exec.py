import logging
import subprocess
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import NamedTuple

import paramiko

logger = logging.getLogger(__name__)


class ExecResult(NamedTuple):
    cmd: tuple[str, ...]
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0


def run_command(cmd: Sequence[str]) -> ExecResult:
    logger.info("Running command '%s'.", " ".join(cmd))
    result = subprocess.run(  # noqa: UP022, S603
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8", check=False
    )

    result = ExecResult(
        cmd=tuple(cmd),
        stdout=result.stdout,
        stderr=result.stderr,
        returncode=result.returncode,
    )
    logger.info("Command '%s' completed with code %d.", " ".join(cmd), result.returncode)
    return result


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
        cmd: Sequence[str],
    ) -> ExecResult:
        session = self.ssh_session.open_channel(kind="session")
        stdout = session.makefile("rb")
        stderr = session.makefile_stderr("rb")
        logger.info("Running command '%s' on host '%s'.", cmd, self.hostname)
        cmd = " ".join(cmd)
        session.exec_command(cmd)
        retval = session.recv_exit_status()
        stdout = stdout.read().decode("utf-8").strip()
        stderr = stderr.read().decode("utf-8").strip()
        if retval:
            logger.error("Command '%s' completed with errors on the remote.", cmd.strip())
            if stderr:
                logger.error(stderr)
        logger.info("Exit status: %d.", retval)
        session.close()
        return ExecResult(
            cmd=tuple(cmd),
            stdout=stdout,
            stderr=stderr,
            returncode=retval,
        )

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
            err_msg = "Can't open channel for upload file via sftp."
            logger.error(err_msg)
            return ExecResult(cmd=(), stderr=err_msg, returncode=1)
        logger.info("Copy '%s' to the remote path '%s'.", localpath, remotepath)
        sftp.put(localpath, str(remotepath))
        sftp.close()
        return ExecResult(
            cmd=("scp", str(localpath), f"{self.username}@{self.hostname}:{remotepath}")
        )

    def download(self, remotepath: Path, localpath: Path) -> ExecResult:
        sftp = paramiko.SFTPClient.from_transport(self.ssh_session)
        if sftp is None:
            err_msg = "Can't open channel for upload file via sftp."
            logger.error(err_msg)
            return ExecResult(cmd=(), stderr=err_msg, returncode=1)
        logger.info("Copy '%s' to the local path '%s'.", remotepath, localpath)
        sftp.get(str(remotepath), localpath)
        sftp.close()
        return ExecResult(
            cmd=("scp", f"{self.username}@{self.hostname}:{remotepath}", str(localpath))
        )


def which(util: str, ssh_client: SSHClient | None = None) -> Path | None:
    call_func = run_command if ssh_client is None else ssh_client
    result = call_func(["which", util])
    if result.returncode:
        return None
    return Path(result.stdout.strip())


def pipeline(
    cmds: Sequence[Sequence[str]], ssh_client: SSHClient | None = None
) -> Iterable[ExecResult]:
    call_func = run_command if ssh_client is None else ssh_client
    for cmd in cmds:
        yield call_func(cmd)
