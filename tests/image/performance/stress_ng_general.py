from itertools import combinations
from typing import TYPE_CHECKING

from imgtests.exec.loaders import StressNg
from imgtests.runner import AbstractRunnableTimeLimitedTest

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


tests = [
    {"cpu": 0, "cpu-method": "matrixprod"},
    {"vm": 3, "vm-bytes": "2G", "mmap": 3, "mmap-bytes": "2G"},
    {"hdd": 0, "hdd-bytes": "2G"},
    {"sock": 2, "netdev": 2, "udp-flood": 2},
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


class StressNgCombineLoadTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Test stress-ng full combine load on subsystems.",
            {"cpu, vm, hdd, network, syscalls, IPC"},
            timeout,
        )

    def _run(self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int) -> None:
        stress_ng = StressNg(client)

        for r in range(2, len(tests)):
            for test_combination in combinations(tests, r):
                test_params = {}

                for params in test_combination:
                    test_params.update(params)

                future = executor.submit(stress_ng.run, timeout_sec=timeout, **test_params)
                result = future.result()
                _, metrics = result
                self.logger.info(metrics)


class StressNgParallelLoadTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Test stress-ng full parallel load on subsystems.",
            {"cpu, vm, hdd, network, syscalls, IPC"},
            timeout,
        )

    def _run(self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int) -> None:
        stress_ng = StressNg(client)

        test_params = {}

        for params in tests:
            test_params.update(params)

        future = executor.submit(stress_ng.run, timeout_sec=timeout, **test_params)
        result = future.result()
        _, metrics = result
        self.logger.info(metrics)
