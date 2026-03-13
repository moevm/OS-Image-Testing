from typing import TYPE_CHECKING

from imgtests.exec.loaders import Chaosblade, StressNg
from imgtests.runner import AbstractRunnableTimeLimitedTest, Subsystem
from imgtests.suites.general.stress_ng import StressNgTest

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


class StressNgPerformanceCpuTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Stress-ng performance CPU test.",
            frozenset({Subsystem.SYSTEM}),
            timeout,
        )

    def _run(self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int) -> None:
        stress_ng = StressNg(client)
        self.run_test(stress_ng=stress_ng, executor=executor, timeout=timeout, cpu=0)


class ChaosbladeCPUTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__("Load CPU 70% with chaosblade.", frozenset({Subsystem.SYSTEM}), timeout)

    def _run(self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int) -> None:
        chaos = Chaosblade(client)
        future = executor.submit(chaos.create_cpu_exp, cpu_percent=70, timeout_sec=timeout)
        _, chaos_result = future.result()
        self.logger.info(chaos_result)
