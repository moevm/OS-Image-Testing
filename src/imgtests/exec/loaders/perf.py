from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient
from imgtests.exec.osinfo import get_os_id
from imgtests.exec.pkgmgrs.zypper import Zypper


class Perf(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("perf", ssh_client)

    def install(self) -> ExecResult:
        """Install perf via the system package manager."""
        os_id = get_os_id(self.ssh_client)
        if os_id and "opensuse" in os_id:
            zypper = Zypper(ssh_client=self.ssh_client)
            return zypper.install(["perf"])

        msg = (
            f"Automatic installation for {self.name!r} is not supported "
            f"on this OS (detected ID: {os_id!r})."
        )
        return ExecResult(
            cmd=self.name,
            stdout="",
            stderr=msg,
            returncode=1,
        )

    def stat(self, cmd: list[str]) -> ExecResult:
        return self(["stat", "--json", *cmd])

    def bench(self, cmd: list[str]) -> ExecResult:
        return self(["bench", *cmd])
