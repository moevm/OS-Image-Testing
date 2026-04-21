from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from imgtests.exec.loaders import PhoronixTestSuite
from imgtests.runner import AbstractRunnableManyTimesTest, TestResult, TestStatus
from imgtests.types import Subsystem

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


class PTSSystemTest(AbstractRunnableManyTimesTest):
    def __init__(self, iterations: int = 1) -> None:
        super().__init__("Load system with PTS.", frozenset({Subsystem.SYSTEM}), iterations)

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        iterations: int,
    ) -> Iterable[TestResult]:
        pts = PhoronixTestSuite(client)
        future = executor.submit(pts.prepare)
        result = future.result()
        if result.returncode:
            self.logger.error("PTS setup failed: '%s'", result.stderr)
            return TestResult(status=TestStatus.BROKEN)

        for test_name in ("pts/ctx-clock", "pts/appleseed"):
            started_at = datetime.now(tz=ZoneInfo("UTC"))
            future = executor.submit(pts.run, test_name=test_name, run_count=iterations)
            result, metrics = future.result()
            if pts.is_timeout_result(result):
                self.logger.error("PTS test '%s' timed out.", test_name)
                yield TestResult(status=TestStatus.BROKEN)
            elif result.returncode:
                self.logger.error("PTS test '%s' FAILED.", test_name)
                yield TestResult(status=TestStatus.FAILED)
            else:
                yield TestResult(
                    command=" ".join(result.cmd),
                    metrics=metrics,
                    started_at=started_at,
                    status=TestStatus.PASSED,
                )
