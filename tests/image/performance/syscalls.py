from typing import TYPE_CHECKING

from imgtests.exec.loaders import StressNg
from imgtests.runner import Subsystem, TestResult
from imgtests.suites.general.stress_ng import StressNgTest

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


class StressNgSyscallsWithCpuLoadTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Stress-ng syscalls test with cpu load scaling cpu percent from 50% to 90%.",
            frozenset({Subsystem.SYSCALLS}),
            timeout,
        )

    def _run(
        self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int
    ) -> Iterable[TestResult]:
        stress_ng = StressNg(client)

        for cpu_percent in range(50, 101, 10):
            yield from self.run_test(
                stress_ng=stress_ng,
                executor=executor,
                timeout=timeout,
                syscall=0,
                syscall_method="all",
                cpu=0,
                **{"cpu-load": cpu_percent},
            )


class StressNgSyscallsWithMemLoadTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Stress-ng syscalls test with memory load.",
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
            vm=0,
            vm_bytes="95%",
        )
