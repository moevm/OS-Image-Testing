import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING, Literal, NamedTuple, overload

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.utils import create_opt

if TYPE_CHECKING:
    from imgtests.exec.exec import ExecResult, SSHClient

logger = logging.getLogger(__name__)


class LoadAverage(NamedTuple):
    minute: float
    minutes5: float
    minutes15: float


class UptimeInfo(NamedTuple):
    curent_time: datetime
    uptime: str
    users: int
    load_avg: LoadAverage


class Uptime(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("uptime", ssh_client)

    @overload
    def __call__(self, since: Literal[False] = False) -> tuple[ExecResult, UptimeInfo | None]: ...

    @overload
    def __call__(self, since: Literal[True]) -> tuple[ExecResult, datetime | None]: ...

    def __call__(self, since: bool = False) -> tuple[ExecResult, UptimeInfo | datetime | None]:
        result = super().__call__([*create_opt("since", since)])
        if result.returncode:
            return result, None
        if since:
            try:
                return result, datetime.strptime(result.stdout, "%Y-%m-%d %H:%M:%S").astimezone()
            except ValueError:
                logger.warning("Failed to parse uptime since.")
                return result, None
        return result, self.parse_uptime(result.stdout)

    @staticmethod
    def parse_uptime(uptime_str: str) -> UptimeInfo | None:
        """Parses string in format "HH:MM:SS up HH:MM, X user(s), load average: L1, L2, L3'."""
        pattern = r"""
            ^(\d{2}:\d{2}:\d{2})\s+up\s+
            (\d{1,2}:\d{1,2}|\d+\s+\w+),\s+
            (\d+)\s+user.*?,\s+
            load\s+average:\s+
            (\d+\.\d+),\s+
            (\d+\.\d+),\s+
            (\d+\.\d+)
        """
        match = re.match(pattern, uptime_str.strip(), re.VERBOSE)
        if match is None:
            return None

        current_time_str, uptime_duration, users_count, load1, load2, load3 = match.groups()
        return UptimeInfo(
            curent_time=datetime.strptime(current_time_str, "%H:%M:%S").astimezone(),
            uptime=uptime_duration,
            users=int(users_count),
            load_avg=LoadAverage(float(load1), float(load2), float(load3)),
        )
