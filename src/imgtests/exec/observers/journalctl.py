from datetime import datetime
from functools import partialmethod
from typing import TYPE_CHECKING, Literal, get_args

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import Verbosity
from imgtests.exec.utils import create_opt

if TYPE_CHECKING:
    from pathlib import Path

    from imgtests.exec.exec import ExecResult, SSHClient


SyslogLevel = Literal["emerg", "alert", "crit", "err", "warning", "notice", "info", "debug"]
CaseSensitive = Literal["yes", "no"]
AlternativeDate = Literal["yesterday", "today", "tomorrow"]


class Journalctl(GenericUtil):
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

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
        output: str | None = None,
        verbosity: Verbosity = Verbosity.STDERR,
        **kwargs: str | float | bool | None,
    ) -> ExecResult:
        """Runs journalctl with provided arguments.

        Args:
            boot (bool): Show messages from a specific boot. Defaults to False.
            priority (SyslogLevel | str | None): Filter output by message priorities or priority
              ranges. Defaults to None.
            grep (str | None): Filter output to entries where the message field matches
              the specified pattern.
            case_sensitive (CaseSensitive): Make pattern matching case sensitive or
              case insensitive.
            since (str | AlternativeDate | None): Show entries from start date.
            until (str | AlternativeDate | None): Show entries to until date.
            output (str | None): Controls how journal records are printed.
            verbosity (Verbosity): Logs verbosity level (stdout, stderr, all, none).
            **kwargs (str | float | bool | None): Command arguments in the free form with values.
        """
        if since is not None:
            self._check_journalctl_date_format(since)
        if until is not None:
            self._check_journalctl_date_format(until)

        opts: list[str | Path] = [
            *create_opt("boot", boot),
            *create_opt("priority", priority),
            *create_opt("grep", grep),
            *create_opt("case-sensitive", case_sensitive, use_equals=True),
            *create_opt("output", output),
        ]
        if since:
            opts.extend(create_opt("since", f"'{since}'"))
        if until:
            opts.extend(create_opt("until", f"'{until}'"))

        return self(opts, verbosity=verbosity, **kwargs)

    systemd_only_records = partialmethod(run, grep="systemd", case_sensitive="no")
    oom_records = partialmethod(run, grep="'Out of memory|OOM'", case_sensitive="no")

    def by_priority_range(
        self,
        lower_bound: int | str,
        upper_bound: int | str | None = None,
    ) -> list[str]:
        """Returns logs by priority range from `a` to `b`."""
        if upper_bound is None:
            upper_bound = lower_bound

        return self.run(boot=True, priority=f"{lower_bound}..{upper_bound}").stdout.split("\n")

    def records_per_second(self) -> float:
        records = self.run(boot=True, output="short-full").stdout.split("\n")

        start = " ".join([records[0].split()[1], records[0].split()[2]])
        end = " ".join([records[-1].split()[1], records[-1].split()[2]])

        start_time = datetime.strptime(start, self.DATE_FORMAT).astimezone()
        end_time = datetime.strptime(end, self.DATE_FORMAT).astimezone()

        delta = end_time - start_time
        delta_secs = delta.total_seconds()

        if delta_secs > 0:
            return len(records) / delta_secs
        if delta_secs == 0:
            return len(records)
        return -1

    @staticmethod
    def calc_records_cnt(raw: str) -> int:
        records = raw.strip().splitlines()
        if len(records) == 1 and "-- no entries --" in records[0].lower():
            return 0
        return len(records)

    @staticmethod
    def _check_journalctl_date_format(date: str) -> None:
        if date in get_args(AlternativeDate):
            return
        datetime.strptime(date, Journalctl.DATE_FORMAT).astimezone()
