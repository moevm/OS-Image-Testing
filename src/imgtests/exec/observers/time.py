import logging
from typing import TYPE_CHECKING, NamedTuple

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult
from imgtests.exec.pkgmgrs.mixin import PkgMgrMixin

if TYPE_CHECKING:
    from imgtests.exec.exec import SSHClient


logger = logging.getLogger(__name__)


class Times(NamedTuple):
    real: float
    user: float
    system: float


class Time(PkgMgrMixin, GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("time", ssh_client)

    def run(self, cmd: str) -> Times | None:
        result = self(["--format", "'%e %U %S'", cmd])
        if result.returncode:
            return None
        lines = result.stderr.splitlines()
        for line in lines:
            raw_time = line.split()
            try:
                return Times(float(raw_time[0]), float(raw_time[1]), float(raw_time[2]))
            except (ValueError, IndexError):
                continue
        return None

    def install(self) -> ExecResult:
        """Install time via the system package manager."""
        if self.path:
            return ExecResult(
                cmd=(), stderr=f"{self.name} already has been installed.", returncode=0
            )
        return self._install_packages(["time"])
