from typing import TYPE_CHECKING

from imgtests.exec.base_util import GenericUtil

if TYPE_CHECKING:
    from imgtests.exec.exec import SSHClient


class Time(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("time", ssh_client)
