from typing import TYPE_CHECKING, NamedTuple

from imgtests.exec.base_util import GenericUtil

if TYPE_CHECKING:
    from imgtests.exec.exec import SSHClient


class JournalctlResult(NamedTuple):
    number_of_records: int
    records: list[str]


class Journalctl(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("journalctl", ssh_client)

    def by_priority(self, lower_bound: int | str, 
                    upper_bound: int | str | None = None) -> JournalctlResult:
        # journalctl -p a..b -> returns logs by priority from `a` to `b`
        # a, b - int or str according to man page
        if upper_bound is None:
            upper_bound = lower_bound

        records = self(["-b", "-p", f"{lower_bound}..{upper_bound}"])

        return JournalctlResult(len(records), records)

    def by_priority_higher(self, lower_bound: int) -> JournalctlResult:
        # journalctl -p a -> returns logs by priority from `a` and higher
        # a - int or str according to man page
        records = self(["-b", "-p", f"{lower_bound}"])

        return JournalctlResult(len(records), records)

    def by_grep(self, target: str):
        records = self(["-b", "-g", f"{target}"])

        return JournalctlResult(len(records), records)        

    def systemd_only(self):
        return self.by_grep("systemd")
    
    def oom_records(self):
        return self.by_grep("OOM")
