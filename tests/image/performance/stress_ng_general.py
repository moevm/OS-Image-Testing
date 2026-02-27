from typing import TYPE_CHECKING

from imgtests.exec.loaders import StressNg
from imgtests.runner import AbstractRunnableTimeLimitedTest

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


tests = [
    {"cpu": 0, "cpu_method": "matrixprod"},
    {"vm": 0, "vm_bytes": "2G"},
    {"hdd": 0, "hdd_bytes": "2G"},
    {"sock": 2, "netdev": 2, "udp_flood": 2},
    {"syscall": 0},
    {"mq": 4, "pipe": 4, "sem": 4, "shm": 4},
]


class StressNgConsecutiveLoadTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Test stress-ng full consecutive load on subsystems.",
            {"cpu, vm, hdd, network, syscalls, IPC"},
            timeout,
        )

    def _run(self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int) -> None:
        stress_ng = StressNg(client)

        for params in tests:
            future = executor.submit(stress_ng.run, timeout_sec=timeout, **params)
            result = future.result()
            _, metrics = result
            self.logger.info(metrics)


class StressNgParallelLoadTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Test stress-ng full consecutive load on subsystems.",
            {"cpu, vm, hdd, network, syscalls, IPC"},
            timeout,
        )

    def _run(self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int) -> None:
        stress_ng = StressNg(client)
        futures = []

        for params in tests:
            future = executor.submit(stress_ng.run, timeout_sec=timeout, **params)
            futures.append(future)

        for future in futures:
            result = future.result()
            _, metrics = result
            self.logger.info(metrics)
