from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from imgtests.exec.exec import SSHClient
from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, common_run_command
from imgtests.exec.osinfo import get_os_release
from imgtests.types import Distro


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


class SystemService(GenericUtil):
    def __init__(self, name: str, ssh_client: SSHClient | None = None) -> None:
        # service -- Yocto
        # systemctl -- opensuse
        self.service = "service"
        os_id = get_os_release(ssh_client).id
        if os_id and os_id == Distro.OPEN_SUSE_LEAP.value:
            self.service = "systemctl"
        super().__init__(name, ssh_client)

    def start_service(self) -> ExecResult:
        if self.service == "service":
            return common_run_command(("sudo", self.service, self.name, "restart"), self.ssh_client)
        return common_run_command(("sudo", self.service, "restart", self.name), self.ssh_client)

    def stop_service(self) -> ExecResult:
        if self.service == "service":
            return common_run_command(("sudo", self.service, self.name, "stop"), self.ssh_client)
        return common_run_command(("sudo", self.service, "stop", self.name), self.ssh_client)

    def check_service(self) -> ExecResult:
        if self.service == "service":
            return common_run_command(("sudo", self.service, self.name, "status"), self.ssh_client)
        return common_run_command(("sudo", self.service, "status", self.name), self.ssh_client)
