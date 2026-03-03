import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from imgtests.exec.base_util import BaseTestUtil
from imgtests.exec.utils import extract_version

if TYPE_CHECKING:
    from imgtests.exec.exec import ExecResult, SSHClient

PGSCAN_LINE_PATTERN = re.compile(
    r"^(\d{2}:\d{2}:\d{2})\s+[\d,]+\s+[\d,]+\s+[\d,]+\s+[\d,]+\s+[\d,]+\s+([\d,]+)\s+([\d,]+)"
)


class Sar(BaseTestUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("sar", ssh_client)

    def version(self):
        result = self(["-V"])
        if result.returncode:
            return None
        return extract_version(result.stdout.strip())

    def run(
        self, interval: int | None = None, count: int | None = None
    ) -> tuple[ExecResult, float]:
        # validation
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
        opts = ["-B"]
        if interval is not None:
            opts.append(interval)
            if interval != 0 and count is not None:
                opts.append(count)

        result = self(opts)

        return result, self.extract_pgscan_time(result.stdout)

    @staticmethod
    def extract_pgscan_time(metrics: str) -> float:
        lines = metrics.strip().split("\n")

        start = None
        duration = 0
        for line in lines:
            m = PGSCAN_LINE_PATTERN.match(line)
            if not m:
                continue

            timestamp_str, pgscank_str, pgscand_str = m.groups()
            pgscank = float(pgscank_str.replace(",", "."))
            pgscand = float(pgscand_str.replace(",", "."))
            timestamp = datetime.strptime(timestamp_str, "%H:%M:%S").replace(tzinfo=UTC)

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
                    timestamp = datetime.strptime(m.group(1), "%H:%M:%S").replace(tzinfo=UTC)
                    duration += (timestamp - start).total_seconds()
                    break
        return duration
