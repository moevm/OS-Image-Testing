from __future__ import annotations

import atexit
import logging
import subprocess
from enum import Flag, auto
from pathlib import Path
from time import sleep
from typing import TYPE_CHECKING, NamedTuple

import paramiko
import paramiko.ssh_exception

from imgtests.environment import env_var_to_type

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

logger = logging.getLogger(__name__)

SSH_CHANNEL_READ_BYTES = 32768


class ExecResult(NamedTuple):
    cmd: tuple[str, ...]
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0


class Verbosity(Flag):
    STDOUT = auto()
    STDERR = auto()


def common_run_command(
    cmd: Sequence[str],
    ssh_client: SSHClient | None = None,
    input_: str | None = None,
    verbosity: Verbosity = Verbosity.STDERR,
) -> ExecResult:
    """Executes a command locally or over SSH, depending on the provided client.

    This function provides a unified way to run a command: if no SSH client is given,
    the command is executed locally using `run_command`; if an SSH client is provided,
    the command is executed through it (assuming the `ssh_client` object has a callable
    interface compatible with `run_command`).

    Args:
        cmd (Sequence[str]): A sequence of strings representing the command and its arguments.
                             Example: ["ls", "-l", "/home/user"].
        ssh_client (SSHClient | None): An SSH client instance for remote execution.
                                       If None, the command runs locally.
        input_ (str | None): Input string to be passed to the command's stdin,
                             useful for interactive commands.
        verbosity (Verbosity): Logs verbosity level (stdout, stderr, all, none).

    Examples:
        >>> result = common_run_command(["echo", "Hello"])
        >>> print(result.stdout)
        Hello
    """
    call_func = run_command if ssh_client is None else ssh_client
    return call_func(cmd=cmd, input_=input_, verbosity=verbosity)


def run_command(
    cmd: Sequence[str],
    input_: str | None = None,
    verbosity: Verbosity = Verbosity.STDERR,
) -> ExecResult:
    """Executes a command locally."""
    logger.debug("Running command '%s'.", " ".join(cmd))
    result = subprocess.run(  # noqa: S603
        cmd,
        input=input_,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )

    result = ExecResult(
        cmd=tuple(cmd),
        stdout=result.stdout.strip(),
        stderr=result.stderr.strip(),
        returncode=result.returncode,
    )
    if Verbosity.STDERR in verbosity and result.returncode:
        logger.error("Command '%s' completed with errors on the local.", " ".join(result.cmd))
        if result.stderr:
            logger.error(result.stderr)
    if Verbosity.STDOUT in verbosity and result.stdout:
        logger.info(result.stdout)
    logger.debug("Command '%s' completed with code %d.", " ".join(cmd), result.returncode)
    return result


class SSHClient:
    __slots__ = ("hostname", "password", "port", "ssh_session", "username")

    def __init__(
        self,
        hostname: str,
        username: str = "root",
        password: str | None = None,
        port: int = 22,
    ) -> None:
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port
        self.ssh_session = paramiko.Transport((self.hostname, self.port))
        logger.info("Connecting to the host '%s'.", self.hostname)
        self.ssh_session.connect(username=self.username, password=self.password)

    @staticmethod
    def _read_available(
        session: paramiko.Channel,
        stdout_chunks: list[bytes],
        stderr_chunks: list[bytes],
    ) -> bool:
        has_read = False
        while session.recv_ready():
            chunk = session.recv(SSH_CHANNEL_READ_BYTES)
            if not chunk:
                break
            stdout_chunks.append(chunk)
            has_read = True

        while session.recv_stderr_ready():
            chunk = session.recv_stderr(SSH_CHANNEL_READ_BYTES)
            if not chunk:
                break
            stderr_chunks.append(chunk)
            has_read = True

        return has_read

    @classmethod
    def _read_until_exit_status_ready(
        cls,
        session: paramiko.Channel,
        stdout_chunks: list[bytes],
        stderr_chunks: list[bytes],
    ) -> None:
        while True:
            has_read = cls._read_available(session, stdout_chunks, stderr_chunks)
            if session.exit_status_ready() and not has_read:
                break
            if not has_read:
                sleep(0.05)

    def __call__(
        self,
        cmd: Sequence[str],
        input_: str | None = None,
        verbosity: Verbosity = Verbosity.STDERR,
    ) -> ExecResult:
        session = self.ssh_session.open_channel(kind="session")
        close_session = session.close
        atexit.register(close_session)
        cmd_str = " ".join(cmd)
        stdout_chunks: list[bytes] = []
        stderr_chunks: list[bytes] = []
        logger.debug("Running command '%s' on host '%s'.", cmd, self.hostname)

        session.exec_command(cmd_str)

        if input_ is not None:
            stdin_channel = session.makefile_stdin("wb")
            stdin_channel.write(input_)
            stdin_channel.flush()
            stdin_channel.close()

        self._read_until_exit_status_ready(session, stdout_chunks, stderr_chunks)
        retval = session.recv_exit_status()

        stdout = b"".join(stdout_chunks).decode("utf-8", errors="replace").strip()
        stderr = b"".join(stderr_chunks).decode("utf-8", errors="replace").strip()

        if Verbosity.STDERR in verbosity and retval:
            logger.error("Command '%s' completed with errors on the remote.", cmd_str)
            if stderr:
                logger.error(stderr)

        if Verbosity.STDOUT in verbosity and stdout:
            logger.info(stdout)

        logger.debug("Exit status: %d.", retval)
        close_session()
        atexit.unregister(close_session)

        return ExecResult(
            cmd=tuple(cmd),
            stdout=stdout,
            stderr=stderr,
            returncode=retval,
        )

    @classmethod
    def build_from_env(
        cls,
        address_env: str,
        user_env: str,
        password_env: str,
        port_env: str,
    ) -> SSHClient:
        return SSHClient(
            env_var_to_type(address_env, str),
            env_var_to_type(user_env, str),
            env_var_to_type(password_env, str),
            env_var_to_type(port_env, int),
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
            cmd=("scp", str(localpath), f"{self.username}@{self.hostname}:{remotepath}"),
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
            cmd=("scp", f"{self.username}@{self.hostname}:{remotepath}", str(localpath)),
        )


def wait_remote(
    address_env: str,
    user_env: str,
    password_env: str,
    port_env: str,
) -> SSHClient | None:
    wait_sec = 60 * 60 * 5
    step_sec = 60
    while wait_sec > 0:
        try:
            return SSHClient.build_from_env(address_env, user_env, password_env, port_env)
        except paramiko.ssh_exception.SSHException:
            logger.info("Waiting remote node to build and run image.")
        sleep(step_sec)
        wait_sec -= 60
    logger.error("Failed to connect to the remote node.")
    return None


def which(util: str, ssh_client: SSHClient | None = None, use_sudo: bool = False) -> Path | None:
    call_func = run_command if ssh_client is None else ssh_client
    for cmd in (
        ["which", util],
        *([["sudo", "which", util]] if use_sudo else []),
    ):
        result = call_func(cmd, verbosity=Verbosity(0))
        if result.returncode:
            continue
        return Path(result.stdout.strip())
    # if which can't find path but tool is installed
    for cmd in (
        ["type", "-p", util],
        *([["sudo", "type", "-p", util]] if use_sudo else []),
    ):
        result = call_func(cmd, verbosity=Verbosity(0))
        if result.returncode:
            continue
        return Path(util)
    return None


def pipeline(
    cmds: Sequence[Sequence[str]],
    ssh_client: SSHClient | None = None,
    pass_output: bool = False,
) -> Iterable[ExecResult]:
    prev_stdout = None

    for cmd in cmds:
        if pass_output and prev_stdout is not None:
            result = common_run_command(cmd, ssh_client=ssh_client, input_=prev_stdout)
        else:
            result = common_run_command(cmd, ssh_client=ssh_client)

        yield result

        if pass_output:
            prev_stdout = result.stdout
