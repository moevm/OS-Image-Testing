from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import SSHClient


class Grep(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("grep", ssh_client)
