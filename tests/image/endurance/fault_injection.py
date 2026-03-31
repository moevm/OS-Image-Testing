import random
from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from imgtests.exec.loaders import Kirk
from imgtests.runner import AbstractRunnableTimeLimitedTest, Subsystem, TestResult, TestStatus

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


class FaultInjectionEnduranceTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int, iterations: int = 4) -> None:
        super().__init__(
            "Endurance test with periodic fault injection.",
            frozenset({Subsystem.SYSTEM}),
            timeout,
        )
        self.iterations = iterations

    def _run(
        self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int
    ) -> Iterable[TestResult]:
        kirk = Kirk(client)
        available_suites = kirk.list_suites()
        if "syscalls" not in available_suites:
            self.logger.warning("'syscalls' suite not available for the image with LTP.")
            return TestResult(status=TestStatus.SKIPPED)
        
        random.seed(timeout)
        fault_probabilities = [random.randint(0, 100) if i % 2 == 1 else 0 for i in range(self.iterations)]
        time_per_test = (timeout // self.iterations) + 1

        for fault_probability in fault_probabilities:
            started_at = datetime.now(tz=ZoneInfo("UTC"))
            result, metrics_path = kirk.run(scenarios=["syscalls"], timeout=time_per_test, fault_injection=fault_probability)

            if metrics_path:
                yield TestResult(
                    command=" ".join(result.cmd),
                    metrics=kirk.metrics_to_json(metrics_path),
                    started_at=started_at,
                    status=TestStatus.PASSED,
                )
            else:
                yield TestResult(
                    command=" ".join(result.cmd),
                    started_at=started_at,
                    status=TestStatus.FAILED,
                )
