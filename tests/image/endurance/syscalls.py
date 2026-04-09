from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from imgtests.exec.loaders import Kirk, StressNg
from imgtests.runner import AbstractRunnableTimeLimitedTest, TestResult, TestStatus
from imgtests.suites.general.stress_ng import StressNgTest
from imgtests.types import Subsystem

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


class LTPSyscallsTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, iterations: int = 1) -> None:
        super().__init__("Test syscalls with LTP.", frozenset({Subsystem.SYSCALLS}), iterations)

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        kirk = Kirk(client)
        available_suites = kirk.list_suites()
        if "syscalls" not in available_suites:
            self.logger.warning("'syscalls' suite not available for the image with LTP.")
            return TestResult(status=TestStatus.SKIPPED)
        started_at = datetime.now(tz=ZoneInfo("UTC"))
        res, metrics_path = kirk.run(["syscalls"], timeout=timeout)
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
        started_at = datetime.now(tz=ZoneInfo("UTC"))
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


class StressNgEnduranceSyscallsTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Stress-ng endurance syscalls test.",
            frozenset({Subsystem.SYSCALLS}),
            timeout,
        )

    def _run(
        self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int
    ) -> Iterable[TestResult]:
        stress_ng = StressNg(client)
        yield from self.run_test(
            stress_ng=stress_ng,
            executor=executor,
            timeout=timeout,
            syscall=0,
            syscall_method="all",
        )
