from typing import TYPE_CHECKING

from imgtests.exec.base_util import GenericUtil

if TYPE_CHECKING:
    from imgtests.exec.exec import SSHClient


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
