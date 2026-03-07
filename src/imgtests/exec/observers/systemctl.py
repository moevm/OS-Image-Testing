from typing import TYPE_CHECKING

from imgtests.exec.base_util import GenericUtil

if TYPE_CHECKING:
    from imgtests.exec.exec import ExecResult, SSHClient


class Systemctl(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None, use_sudo: bool = True) -> None:
        super().__init__("systemctl", ssh_client, use_sudo=use_sudo)

    def start(self, service: str) -> ExecResult:
        return self(["start", service])

    def restart(self, service: str) -> ExecResult:
        return self(["restart", service])

    def stop(self, service: str) -> ExecResult:
        return self(["stop", service])

    def status(self, service: str) -> ExecResult:
        return self(["status", service])

    def get_failed_services(self) -> set[str]:
        result = self(["--failed", "--no-legend"])
        if result.returncode:
            return set()
        result = result.stdout
        try:
            return {
                line.split()[1]
                for line in result.split("\n")
                if line and line.split()[1].endswith(".service")
            }
        except IndexError:
            return set()

    def get_running_services(self) -> set[str]:
        result = self(["list-units", "--type=service", "--state=running", "--no-legend"])
        if result.returncode:
            return set()
        result = result.stdout
        try:
            return {
                line.split()[0]
                for line in result.split("\n")
                if line and line.split()[0].endswith(".service")
            }
        except IndexError:
            return set()
