from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, get_args

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.utils import create_opt

if TYPE_CHECKING:
    from imgtests.exec.exec import ExecResult, SSHClient


SyslogLevel = Literal["emerg", "alert", "crit", "err", "warning", "notice", "info", "debug"]
CaseSensitive = Literal["yes", "no"]
AlternativeDate = Literal["yesterday", "today", "tomorrow"]


class Journalctl(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None, use_sudo: bool = False) -> None:
        super().__init__("journalctl", ssh_client, use_sudo=use_sudo)

    def run(  # noqa: PLR0913
        self,
        boot: bool = False,
        priority: SyslogLevel | str | None = None,
        grep: str | None = None,
        case_sensitive: CaseSensitive = "yes",
        since: str | AlternativeDate | None = None,
        until: str | AlternativeDate | None = None,
        **kwargs: dict[str, Any],
    ) -> ExecResult:
        """Runs journalctl with provided arguments.

        Args:
            boot (bool): Show messages from a specific boot. Defaults to False.
            priority (SyslogLevel | str | None): Filter output by message priorities or priority
              ranges. Defaults to None.
            grep(str): Filter output to entries where the message field matches the specified
              pattern.
            case_sensitive(CaseSensitive): Make pattern matching case sensitive or case insensitive.
            since(str): Show entries from start date.
            until(str): Show entries to until date.
            **kwargs (dict[str, Any]): Command arguments in the free form with values.
        """
        if since is not None:
            self._check_journalctl_date_format(since)
        if until is not None:
            self._check_journalctl_date_format(until)

        return self(
            [
                *create_opt("boot", boot),
                *create_opt("priority", priority),
                *create_opt("grep", grep),
                *create_opt("case-sensitive", case_sensitive),
            ],
            **kwargs,
        )

    def by_priority_range(
        self, lower_bound: int | str, upper_bound: int | str | None = None
    ) -> list[str]:
        """Returns logs by priority range from `a` to `b`."""
        if upper_bound is None:
            upper_bound = lower_bound

        return self.run(boot=True, priority=f"{lower_bound}..{upper_bound}").stdout.split("\n")

    def systemd_only(self) -> list[str]:
        return self.run(grep="systemd").stdout.split("\n")

    def oom_records(self) -> list[str]:
        return self.run(grep="Out of memory|OOM", case_sensitive="no").stdout.split("\n")

    def records_per_second(self) -> float:
        records = self(["--boot", "-o", "short-full"]).stdout.split("\n")

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

    @staticmethod
    def _check_journalctl_date_format(date: str) -> None:
        if date in get_args(AlternativeDate):
            return
        journalctl_format = "%Y-%m-%d %H:%M:%S"
        datetime.strptime(date, journalctl_format).astimezone()
