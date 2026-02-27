from typing import TYPE_CHECKING

from imgtests.exec.loaders import Kirk, StressNg
from imgtests.runner import AbstractRunnableManyTimesTest, AbstractRunnableTimeLimitedTest

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


class LTPSyscallsTest(AbstractRunnableManyTimesTest):
    def __init__(self, iterations: int = 1) -> None:
        super().__init__("Test syscalls with LTP.", {"syscalls"}, iterations)

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


class StressNgAllSyscallsTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__("Test syscalls performance with stress-ng.", {"syscalls"}, timeout)

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        timeout: int,
    ) -> None:
        stress_ng = StressNg(client)
        result, (metrics, summary) = stress_ng.run(
            timeout_sec=timeout,
            syscall=0,
            syscall_method="all",
        )
        if result.returncode:
            self.logger.error("stress-ng syscalls failed")
        else:
            self.logger.info(summary)
            self.logger.info(metrics)
