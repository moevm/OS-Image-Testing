from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import SSHClient


class MkDir(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("mkdir", ssh_client)


class Rm(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("rm", ssh_client)
