from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import SSHClient


class RPM(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("rpm", ssh_client)

    def get_pkglist(self) -> tuple[str, ...]:
        return tuple(self(["-qa"]).stdout.strip().split("\n"))
