from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from imgtests.exec.loaders import Kirk, StressNg
from imgtests.runner import AbstractRunnableTimeLimitedTest, Subsystem, TestResult
from imgtests.suites.general.stress_ng import StressNgTest

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


class SyscallsWithCpuLoadTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Syscalls test with cpu load scaling cpu percent from 50% to 100%.",
            frozenset({Subsystem.SYSCALLS}),
            timeout,
        )

    def _run(
        self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int
    ) -> Iterable[TestResult]:
        stress_ng = StressNg(client)
        kirk = Kirk(client)

        # cpu load 50%, 60%, ..., 100%
        for cpu_percent in range(50, 101, 10):
            started_at = datetime.now(tz=ZoneInfo("UTC"))
            future_kirk = executor.submit(kirk.run, ["syscalls"])

            future_stress_ng = executor.submit(
                stress_ng.run,
                timeout=timeout,
                syscall=0,
                syscall_method="all",
                cpu=0,
                **{"cpu-load": cpu_percent},
            )
            stress_ng_res, stress_ng_metrics = future_stress_ng.result()
            _, kirk_metrics_path = future_kirk.result()

            self.logger.info("Finished test with %d load", cpu_percent)

            yield TestResult(
                # TODO: update command with LTP
                command=" ".join(stress_ng_res.cmd),
                metrics={
                    **stress_ng.metrics_to_json(stress_ng_metrics),
                    **kirk.metrics_to_json(kirk_metrics_path),
                },
                started_at=started_at,
                ended_at=datetime.now(tz=ZoneInfo("UTC")),
            )
            self.cleanup(client, self.logger)


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
