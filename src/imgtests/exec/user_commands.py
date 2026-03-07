from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from imgtests.exec.exec import ExecResult, SSHClient
from imgtests.exec.base_util import GenericUtil


class MkDir(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("mkdir", ssh_client)


class Rm(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("rm", ssh_client)


class Dd(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("dd", ssh_client)


class Mdadm(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("mdadm", ssh_client)


class Lsblk(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("lsblk", ssh_client)


class Systemctl(GenericUtil):
    def __init__(
        self, name: str, ssh_client: SSHClient | None = None, use_sudo: bool = True
    ) -> None:
        self.service = name
        super().__init__("systemctl", ssh_client, use_sudo=use_sudo)

    def restart(self) -> ExecResult:
        return self(["restart", self.service])

    def stop(self) -> ExecResult:
        return self(["stop", self.service])

    def status(self) -> ExecResult:
        return self(["status", self.service])
