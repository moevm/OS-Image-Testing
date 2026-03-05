from datetime import datetime
from typing import TYPE_CHECKING, NamedTuple

from imgtests.exec.base_util import GenericUtil

if TYPE_CHECKING:
    from imgtests.exec.exec import SSHClient


class JournalctlResult(NamedTuple):
    number_of_records: int
    records: list[str]


class Journalctl(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("journalctl", ssh_client, use_sudo=True)

    @staticmethod
    def _validate_time(line: str) -> bool:
        journalctl_format = "%Y-%m-%d %H:%M:%S"
        try:
            datetime.strptime(line, journalctl_format).astimezone()
        except ValueError:
            return False
        return True

    def by_priority(
        self, lower_bound: int | str, upper_bound: int | str | None = None
    ) -> JournalctlResult:
        # journalctl -p a..b -> returns logs by priority from `a` to `b`
        # a, b - int or str according to man page
        if upper_bound is None:
            upper_bound = lower_bound

        records = self(["-b", "-p", f"{lower_bound}..{upper_bound}"]).stdout.split("\n")

        return JournalctlResult(len(records), records)

    def by_priority_higher(self, lower_bound: int) -> JournalctlResult:
        # journalctl -p a -> returns logs by priority from `a` and higher
        # a - int or str according to man page
        records = self(["-b", "-p", f"{lower_bound}"]).stdout.split("\n")

        return JournalctlResult(len(records), records)

    def by_grep(self, target: str) -> JournalctlResult:
        records = self(["-b", "-g", f"{target}"]).stdout.split("\n")

        return JournalctlResult(len(records), records)

    def systemd_only(self) -> JournalctlResult:
        return self.by_grep("systemd")

    def oom_records(self) -> JournalctlResult:
        return self.by_grep("OOM")

    def from_time_period(self, since: str, until: str | None = None) -> JournalctlResult | None:
        if not self._validate_time(since):
            return None

        if until is not None and not self._validate_time(until):
            return None

        cmd = ["-S", f'"{since}"']
        if until is not None:
            cmd.append("-U")
            cmd.append(f'"{until}"')
        records = self([*cmd]).stdout.split("\n")

        return JournalctlResult(len(records), records)

    def records_per_second(self) -> float:
        records = self(["-b", "-o", "short-full"]).stdout.split("\n")

        start = " ".join([records[0].split()[1], records[0].split()[2]])
        end = " ".join([records[-1].split()[1], records[-1].split()[2]])

        time_format = "%Y-%m-%d %H:%M:%S"
        start_time = datetime.strptime(start, time_format).astimezone()
        end_time = datetime.strptime(end, time_format).astimezone()

        delta = end_time - start_time
        delta_secs = delta.total_seconds()

        if delta_secs > 0:
            return len(records) / delta_secs
        return -1
