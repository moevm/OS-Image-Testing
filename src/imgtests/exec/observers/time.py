from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import SSHClient


class Time(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("/usr/bin/time", ssh_client)
