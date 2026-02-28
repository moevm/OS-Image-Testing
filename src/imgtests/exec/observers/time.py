from typing import TYPE_CHECKING, NamedTuple

from imgtests.exec.base_util import GenericUtil

if TYPE_CHECKING:
    from imgtests.exec.exec import SSHClient


class Times(NamedTuple):
    real: float
    user: float
    system: float


class Time(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("time", ssh_client)

    def run(self, cmd: str) -> Times | None:
        result = self(["--format", "'%e %U %S'", cmd])
        if result.returncode:
            return None
        raw_time = result.stderr.split()
        try:
            return Times(float(raw_time[0]), float(raw_time[1]), float(raw_time[2]))
        except (ValueError, IndexError):
            return None
