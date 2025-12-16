from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient, common_run_command
from imgtests.exec.loaders.fio import PkgMgrMixin


class Pip3(PkgMgrMixin, GenericUtil):
    """Wrapper around the pip3 Python package manager, working over SSH or locally."""

    def __init__(
        self,
        ssh_client: SSHClient | None = None,
    ) -> None:
        super().__init__("pip3", ssh_client)

    def install(self) -> ExecResult:
        result = common_run_command(["pip3", "--version"], self.ssh_client)
        if result.returncode:
            result = self._install_packages(["python3-pip"])
        return result
