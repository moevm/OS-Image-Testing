from datetime import UTC, datetime
from typing import TYPE_CHECKING

from imgtests.exec.loaders import Kirk, Perf
from imgtests.planning import AbstractRunnableManyTimesTest, AbstractRunnableTimeLimitedTest
from imgtests.types import Subsystem, TestResult, TestStatus

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


class SchedPerformanceTest(AbstractRunnableManyTimesTest):
    def __init__(self, iterations: int = 1) -> None:
        super().__init__(
            "Benchmark scheduler and IPC mechanisms.",
            frozenset({Subsystem.IPC}),
            iterations,
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        iterations: int,
    ) -> Iterable[TestResult]:
        perf = Perf(client)
        for benchmark, args in zip(
            ["messaging", "messaging", "pipe"],
            [[], ["--thread"], []],
            strict=True,
        ):
            started_at = datetime.now(UTC)
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


class LTPSyscallsIPCTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, iterations: int = 1) -> None:
        super().__init__(
            "Test syscalls-ipc with LTP.",
            frozenset({Subsystem.IPC, Subsystem.SYSCALLS}),
            iterations,
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        kirk = Kirk(client)
        available_suites = kirk.list_suites()
        if "syscalls-ipc" not in available_suites:
            self.logger.warning("'syscalls-ipc' suite not available for the image with LTP.")
            return TestResult(status=TestStatus.SKIPPED)
        started_at = datetime.now(UTC)
        res, metrics_path = kirk.run(["syscalls-ipc"], timeout=timeout)
        if metrics_path:
            yield TestResult(
                command=" ".join(res.cmd),
                metrics=kirk.metrics_to_json(metrics_path),
                started_at=started_at,
                status=TestStatus.PASSED,
            )
        else:
            yield TestResult(
                command=" ".join(res.cmd),
                started_at=started_at,
                status=TestStatus.FAILED,
            )
