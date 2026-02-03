from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import SSHClient


class Dd(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("dd", ssh_client)
