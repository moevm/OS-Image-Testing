from typing import TYPE_CHECKING

from imgtests.exec.loaders import Chaosblade, StressNg
from imgtests.runner import AbstractRunnableTimeLimitedTest

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


class StressNgCpuTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__("Load CPU with stress-ng.", {"system"}, timeout)

    def _run(self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int) -> None:
        stress_ng = StressNg(client)
        future = executor.submit(stress_ng.run, timeout_sec=timeout, cpu=0)
        result = future.result()
        _, metrics = result
        self.logger.info(metrics)


class ChaosbladeCPUTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__("Load CPU 70% with chaosblade.", {"system"}, timeout)

    def _run(self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int) -> None:
        chaos = Chaosblade(client)
        future = executor.submit(chaos.create_cpu_exp, cpu_percent=70, timeout_sec=timeout)
        _, chaos_result = future.result()
        self.logger.info(chaos_result)
