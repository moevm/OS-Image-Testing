from typing import TYPE_CHECKING, Any

from imgtests.runner import AbstractRunnableTimeLimitedTest

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.loaders import StressNg


class StressNgTest(AbstractRunnableTimeLimitedTest):
    def run_test(
        self,
        stress_ng: StressNg,
        executor: ThreadPoolExecutor,
        timeout: int,
        **kwargs: dict[str, Any],
    ) -> None:
        future = executor.submit(stress_ng.run, timeout_sec=timeout, **kwargs)
        result, (metrics, summary) = future.result()

        if result.returncode:
            self.logger.error("stress-ng test FAILED")

        if metrics:
            self.logger.info(metrics)
        if summary:
            self.logger.info(summary)
