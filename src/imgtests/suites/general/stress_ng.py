from datetime import UTC, datetime
from typing import TYPE_CHECKING

from imgtests.exec.loaders import StressNgParamVerValidationError
from imgtests.planning import AbstractRunnableTimeLimitedTest
from imgtests.types import TestResult, TestStatus

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
        **kwargs: str | float | bool | None,
    ) -> Iterable[TestResult]:
        started_at = datetime.now(UTC)
        future = executor.submit(stress_ng.run, timeout_sec=timeout, **kwargs)
        try:
            result, metrics = future.result()
        except StressNgParamVerValidationError as err:
            self.logger.warning("stress-ng test skipped due absent of options: %s", err)
            yield TestResult(status=TestStatus.SKIPPED)
            return

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
