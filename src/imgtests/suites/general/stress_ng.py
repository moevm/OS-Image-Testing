from datetime import datetime
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from imgtests.runner import AbstractRunnableTimeLimitedTest, TestResult, TestStatus

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.loaders import StressNg


class StressNgTest(AbstractRunnableTimeLimitedTest):
    def run_test(
        self,
        stress_ng: StressNg,
        executor: ThreadPoolExecutor,
        timeout: int,
        **kwargs: dict[str, Any],
    ) -> Iterable[TestResult]:
        started_at = datetime.now(tz=ZoneInfo("UTC"))
        future = executor.submit(stress_ng.run, timeout_sec=timeout, **kwargs)
        result, metrics = future.result()

        if result.returncode == stress_ng.INCORRECT_OPT_OR_FATAL_ISSUE_CODE:
            self.logger.error("stress-ng test BROKEN")
            yield TestResult(status=TestStatus.BROKEN)
            return
        elif result.returncode:
            self.logger.error("stress-ng test FAILED")
            yield TestResult(status=TestStatus.FAILED)
            return

        yield TestResult(
            metrics=stress_ng.metrics_to_json(metrics),
            command=" ".join(result.cmd),
            started_at=started_at,
            status=TestStatus.PASSED,
        )
