import logging
from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from imgtests.exec.loaders import StressNg
from imgtests.exec.observers import Sar
from imgtests.runner import AbstractRunnableTimeLimitedTest, Subsystem, TestResult

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient

logger = logging.getLogger(__name__)


class SarWithStressNGTest(AbstractRunnableTimeLimitedTest):
    """Tests that run stress-ng with sar to measure pgscan time."""

    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Stress-ng with sar measure pgscan time.", frozenset({Subsystem.MEMORY}), timeout
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        sar = Sar(client)

        stress_ng = StressNg(client)
        started_at = datetime.now(tz=ZoneInfo("UTC"))
        stress_ng_future = executor.submit(
            stress_ng.run,
            timeout_sec=timeout,
            vm=4,
            vm_bytes="95%",
        )

        _, pgscan = sar.run(interval=1, count=timeout)
        result, (metrics, summary) = stress_ng_future.result()

        yield TestResult(
            metrics={
                "pgscan_time_sec": pgscan,
                "stress_ng_metrics": metrics,
                "stress_ng_summary": summary,
            },
            command=" ".join(result.cmd),
            started_at=started_at,
        )
