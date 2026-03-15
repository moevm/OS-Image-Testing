import logging
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal, get_args

from imgtests.exec.base_util import BaseTestUtil
from imgtests.exec.exec import ExecResult, pipeline
from imgtests.exec.osinfo import get_os_release
from imgtests.exec.pkgmgrs.mixin import PkgMgrMixin
from imgtests.exec.utils import extract_version

if TYPE_CHECKING:
    from imgtests.exec.exec import SSHClient

PGSCAN_LINE_PATTERN = re.compile(
    r"^(?P<timestamp>\d{2}:\d{2}:\d{2}(?:\s+[AP]M)?)\s+"
    r"[\d,.]+\s+[\d,.]+\s+[\d,.]+\s+[\d,.]+\s+[\d,.]+\s+"
    r"(?P<pgscank>[\d,.]+)\s+"
    r"(?P<pgscand>[\d,.]+)"
)

logger = logging.getLogger(__name__)

ReportTypes = Literal["A", "B", "b", "C", "D", "d", "H", "S", "v", "W", "w", "y"]


class Sar(PkgMgrMixin, BaseTestUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("sar", ssh_client)

    def version(self):
        result = self(["-V"])
        if result.returncode:
            return None
        return extract_version(result.stdout.strip())

    def install(self) -> ExecResult:
        """Install sysstat with sar via the system package manager."""
        if self.path:
            return ExecResult(
                cmd=(), stderr=f"{self.name} already has been installed.", returncode=0
            )
        return self._install_packages(["sysstat"])

    def run(
        self,
        report_type: ReportTypes = "B",
        interval: int | None = None,
        count: int | None = None,
        **kwargs: dict[str, Any],
    ) -> tuple[ExecResult, int]:
        """Run sar with parameters.

        Args:
            report_type (ReportTypes): Subsystem activity report flag. Default is 'B' for paging.
            interval (int | None): Measurement time interval
            count (int | None): Number of measurements
            **kwargs (dict[str, Any]): Command arguments in the free form with values.

        Returns:
            tuple[ExecResult, int]: Result of sar and parsed pgscan time

        Raises:
            ValueError: When invalid parameters provided or repeated.
        """
        # validation
        if report_type not in get_args(ReportTypes):
            err_msg = f"Invalid type '{report_type}'. Type should be one of {get_args(ReportTypes)}"
            raise ValueError(err_msg)

        if interval is None and count is not None:
            err_msg = "If interval is None, count should be set None."
            raise ValueError(err_msg)

        if interval is not None and interval < 0:
            err_msg = f"Invalid interval '{interval}'. Expected more or equal 0."
            raise ValueError(err_msg)

        if interval is not None and interval == 0 and count is not None:
            err_msg = "If interval is '0', count should not be set."
            raise ValueError(err_msg)

        if interval is not None and interval != 0 and count is None:
            err_msg = "If interval is not equal 0, count should not be None."
            raise ValueError(err_msg)

        if count is not None and count <= 0:
            err_msg = f"Invalid count '{count}'. Expected more than 0."
            raise ValueError(err_msg)

        # create command
        opts = [f"-{type}"]
        if interval is not None:
            opts.append(interval)
            if interval != 0 and count is not None:
                opts.append(count)

        result = self(
            opts,
            **kwargs,
        )

        return result, self.extract_pgscan_time(result.stdout)

    @staticmethod
    def extract_pgscan_time(metrics: str) -> float:
        """Parses pgcan time.

        Args:
            metrics (str): Metric string returned by sar

        Returns:
            float: pgscan time in seconds
        """
        lines = metrics.strip().split("\n")

        time_fmt = "%I:%M:%S %p" if re.search(r"\d{2}:\d{2}:\d{2}\s+[AP]M", metrics) else "%H:%M:%S"

        start = None
        duration = 0
        for line in lines:
            m = PGSCAN_LINE_PATTERN.match(line)
            if not m:
                continue

            pgscank = float(m.group("pgscank").replace(",", "."))
            pgscand = float(m.group("pgscand").replace(",", "."))
            timestamp = datetime.strptime(m.group("timestamp"), time_fmt).replace(tzinfo=UTC)

            if pgscand > 0 or pgscank > 0:
                if start is None:
                    start = timestamp
            elif start is not None:
                duration += (timestamp - start).total_seconds()
                start = None

        if start is not None:
            for line in reversed(lines):
                m = PGSCAN_LINE_PATTERN.match(line)
                if m:
                    timestamp = datetime.strptime(m.group("timestamp"), time_fmt).replace(
                        tzinfo=UTC
                    )
                    duration += (timestamp - start).total_seconds()
                    break
        return duration

    def prepare(self) -> ExecResult | None:
        """Starts automatic collection of metrics.

        Is required to use the utility without parameters interval and count.
        """
        os_id = get_os_release(self.ssh_client).id
        if os_id and "opensuse" in os_id:
            cmds = [
                ["sudo", "sed", "-i", 's/ENABLED="false"/ENABLED="true"/', "/etc/sysstat/sysstat"],
                ["sudo", "systemctl", "enable", "--now", "sysstat_collect.timer"],
                ["sudo", "systemctl", "enable", "--now", "sysstat_summary.timer"],
            ]
        else:
            cmds = [
                [
                    "sudo",
                    "sed",
                    "-i",
                    's/ENABLED="false"/ENABLED="true"/',
                    "/etc/sysconfig/sysstat",
                ],
                ["sudo", "systemctl", "enable", "--now", "sysstat"],
                [
                    "echo -e '*/10 * * * * root /usr/libexec/sa/sa1 1 1\n",
                    "23:59 * * * * root /usr/libexec/sa/sa2 -A'",
                    "| sudo tee /etc/cron.d/sysstat",
                ],
                ["sudo", "chmod", "644", "/etc/cron.d/sysstat"],
                ["sudo", "systemctl", "enable", "--now", "crond"],
            ]
        last_r = None
        for r in pipeline(cmds, ssh_client=self.ssh_client):
            last_r = r
            if r.returncode != 0:
                logger.error("Prepare failed: %s", r)
                return r
        return last_r
