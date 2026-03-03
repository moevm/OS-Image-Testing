from datetime import datetime
from typing import TYPE_CHECKING, NamedTuple

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import common_run_command

if TYPE_CHECKING:
    from imgtests.exec.exec import SSHClient


class JournalctlResult(NamedTuple):
    number_of_records: int
    records: list[str]


class Journalctl(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("journalctl", ssh_client)

    def by_priority(
        self, lower_bound: int | str, upper_bound: int | str | None = None
    ) -> JournalctlResult:
        # journalctl -p a..b -> returns logs by priority from `a` to `b`
        # a, b - int or str according to man page
        if upper_bound is None:
            upper_bound = lower_bound

        records = common_run_command(
            ("sudo", self.name, "-b", "-p", f"{lower_bound}..{upper_bound}"), self.ssh_client
        ).stdout.split("\n")

        return JournalctlResult(len(records), records)

    def by_priority_higher(self, lower_bound: int) -> JournalctlResult:
        # journalctl -p a -> returns logs by priority from `a` and higher
        # a - int or str according to man page
        records = common_run_command(
            ("sudo", self.name, "-b", "-p", f"{lower_bound}"), self.ssh_client
        ).stdout.split("\n")

        return JournalctlResult(len(records), records)

    def by_grep(self, target: str):
        records = common_run_command(
            ("sudo", self.name, "-b", "-g", f"{target}"), self.ssh_client
        ).stdout.split("\n")

        return JournalctlResult(len(records), records)

    def systemd_only(self):
        return self.by_grep("systemd")

    def oom_records(self):
        return self.by_grep("OOM")

    def records_per_second(self) -> float:
        records = common_run_command(
            ("sudo", self.name, "-b", "-o", "short-full"), self.ssh_client
        ).stdout.split("\n")

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
