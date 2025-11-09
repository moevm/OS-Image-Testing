from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import SSHClient


class Kirk(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("kirk", ssh_client)
