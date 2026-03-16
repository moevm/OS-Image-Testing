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

    def enable(self, service: str) -> ExecResult:
        return self(["enable", service])

    def daemon_reload(self) -> ExecResult:
        return self(["daemon-reload"])

    def get_failed_services(self) -> tuple[ExecResult, set[str]]:
        result = self(["--failed", "--no-legend"])
        if result.returncode:
            return result, set()
        try:
            return result, {
                line.split()[1]
                for line in result.stdout.split("\n")
                if line and line.split()[1].endswith(".service")
            }
        except IndexError:
            return result, set()

    def get_running_services(self) -> tuple[ExecResult, set[str]]:
        result = self(["list-units", "--type=service", "--state=running", "--no-legend"])
        if result.returncode:
            return result, set()
        try:
            return result, {
                line.split()[0]
                for line in result.stdout.split("\n")
                if line and line.split()[0].endswith(".service")
            }
        except IndexError:
            return result, set()

    @staticmethod
    def metrics_to_json(metrics: set[str]) -> list:
        return list(metrics)
