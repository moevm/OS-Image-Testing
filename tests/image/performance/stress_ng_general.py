from itertools import combinations
from typing import TYPE_CHECKING

from imgtests.exec.loaders import StressNg
from imgtests.suites.drive.stress_ng import StressNgTest

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


tests = [
    {"cpu": 0, "cpu_method": "matrixprod"},
    {"vm": 3, "vm_bytes": "2G", "mmap": 3, "mmap_bytes": "2G"},
    {"hdd": 0, "hdd_bytes": "2G"},
    {"sock": 2, "netdev": 2, "udp_flood": 2},
    {"syscall": 0},
    {"mq": 4, "pipe": 4, "sem": 4, "shm": 4},
]


def combine_params(test_combination: list) -> dict:
    """Combines params from list of dictionaries into single dictionary.

    Args:
        test_combination (list): List of test scenarios.

    Returns:
        dict: Single dictionary with all test params.
    """
    test_params = {}
    for params in test_combination:
        test_params.update(params)
    return test_params


class StressNgConsecutiveLoadTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Test stress-ng full consecutive load on subsystems.",
            {"memory", "file", "IPC", "syscalls", "network", "system"},
            timeout,
        )

    def _run(self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int) -> None:
        stress_ng = StressNg(client)

        for params in tests:
            self.run_test(stress_ng=stress_ng, executor=executor, timeout=timeout, **params)


class StressNgCombineLoadTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Test stress-ng full combine load on subsystems.",
            {"memory", "file", "IPC", "syscalls", "network", "system"},
            timeout,
        )

    def _run(self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int) -> None:
        stress_ng = StressNg(client)

        for r in range(2, len(tests)):
            for test_combination in combinations(tests, r):
                test_params = combine_params(test_combination)
                self.run_test(stress_ng=stress_ng, executor=executor, timeout=timeout, **test_params)


class StressNgParallelLoadTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Test stress-ng full parallel load on subsystems.",
            {"memory", "file", "IPC", "syscalls", "network", "system"},
            timeout,
        )

    def _run(self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int) -> None:
        stress_ng = StressNg(client)

        test_params = combine_params(tests)
        self.run_test(stress_ng=stress_ng, executor=executor, timeout=timeout, **test_params)
