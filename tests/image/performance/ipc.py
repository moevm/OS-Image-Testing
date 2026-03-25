from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from imgtests.exec.loaders import Perf
from imgtests.runner import AbstractRunnableManyTimesTest, Subsystem, TestResult, TestStatus

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


class SchedPerformanceTest(AbstractRunnableManyTimesTest):
    def __init__(self, iterations: int = 1) -> None:
        super().__init__(
            "Benchmark scheduler and IPC mechanisms.", frozenset({Subsystem.IPC}), iterations
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        iterations: int,
    ) -> Iterable[TestResult]:
        perf = Perf(client)
        for benchmark, args in zip(
            ["messaging", "messaging", "pipe"], [[], ["--thread"], []], strict=True
        ):
            started_at = datetime.now(tz=ZoneInfo("UTC"))
            result, metrics = perf.bench("sched", benchmark, args, repeat=iterations)
            metrics_json = {}
            if result.returncode:
                self.logger.error("Failed to run benchmark '%s' with args '%s'.", benchmark, args)
                status = TestStatus.FAILED
            else:
                status = TestStatus.PASSED
                metrics_json = perf.metrics_to_json(metrics)
            yield TestResult(
                started_at=started_at,
                metrics=metrics_json,
                command=" ".join(result.cmd),
                status=status,
            )
