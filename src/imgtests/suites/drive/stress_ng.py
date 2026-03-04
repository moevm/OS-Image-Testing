from typing import TYPE_CHECKING

from imgtests.exec.loaders import StressNg
from imgtests.runner import AbstractRunnableTimeLimitedTest

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor


class StressNgTest(AbstractRunnableTimeLimitedTest):
    def combine_params(self, test_combination: list) -> dict:
        """Combines params from list of dictionaries into single dictionary.

        Args:
            test_combination (list): List of test scenarios.

        Returns:
            dict: Single dictionary with all test params.
        """
        test_params = {}
        for params in test_combination:
            test_params.update(params)
        return test_params

    def run_test(
        self, stress_ng: StressNg, executor: ThreadPoolExecutor, timeout: int, params: dict
    ) -> None:
        future = executor.submit(stress_ng.run, timeout_sec=timeout, **params)
        result, (metrics, summary) = future.result()

        if result.returncode:
            self.logger.error("stress-ng test FAILED")

        if metrics:
            self.logger.info(metrics)
        if summary:
            self.logger.info(summary)
