from typing import TYPE_CHECKING

from imgtests.exec.loaders import Kirk, StressNg
from imgtests.runner import AbstractRunnableManyTimesTest, Subsystem, TestResult
from imgtests.suites.general.stress_ng import StressNgTest

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


class LTPSyscallsTest(AbstractRunnableManyTimesTest):
    def __init__(self, iterations: int = 1) -> None:
        super().__init__("Test syscalls with LTP.", frozenset({Subsystem.SYSCALLS}), iterations)

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        iterations: int,  # noqa: ARG002
    ) -> None:
        kirk = Kirk(client)
        available_suites = kirk.list_suites()
        if "syscalls" not in available_suites:
            self.logger.warning("'syscalls' suite not available for the image with LTP.")
            return
        kirk.run(["syscalls"])


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
