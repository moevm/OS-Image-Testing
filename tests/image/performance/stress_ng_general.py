from itertools import combinations
from typing import TYPE_CHECKING, Any

from imgtests.exec.exec import common_run_command
from imgtests.exec.loaders import StressNg
from imgtests.runner import Subsystem, TestResult
from imgtests.suites.general.stress_ng import StressNgTest

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


tests: list[dict[str, Any]] = [
    {"cpu": 0, "cpu_method": "matrixprod"},
    {"vm": 0, "vm_bytes": "90%", "mmap": 0, "mmap_bytes": "90%"},
    {"hdd": 0, "hdd_bytes": "90%"},
    {"sock": 0, "netdev": 0, "udp_flood": 0},
    {"syscall": 0},
    {"mq": 0, "pipe": 0, "sem": 0, "shm": 0},
]


def combine_params(test_combination: list[dict[str, Any]]) -> dict[str, Any]:
    """Combines params from list of dictionaries into single dictionary.

    Args:
        test_combination (list): List of test scenarios.

    Returns:
        dict: Single dictionary with all test params.
    """
    test_params: dict[str, Any] = {}
    for params in test_combination:
        test_params.update(params)
    return test_params


def tests_config(client: SSHClient | None):
    nproc_result = common_run_command(["nproc"], client)
    nproc = int(nproc_result.stdout)
    net_param = int(nproc / 2) if nproc > 1 else 1
    net = {
        "sock": net_param,
        "netdev": net_param,
        "udp_flood": net_param,
    }
    if net not in tests:
        tests.append(net)
    ipc_param = int(nproc * 3 / 4) if nproc > 1 else 1
    ipc = {
        "mq": ipc_param,
        "pipe": ipc_param,
        "sem": ipc_param,
        "shm": ipc_param,
    }
    syscall_param = int(nproc / 2) if nproc > 1 else 1
    syscall = {"syscall": syscall_param}
    if syscall not in tests:
        tests.append(syscall)
    if ipc not in tests:
        tests.append(ipc)


class StressNgConsecutiveLoadTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Test stress-ng full consecutive load on subsystems.",
            frozenset(
                {
                    Subsystem.MEMORY,
                    Subsystem.FILE,
                    Subsystem.IPC,
                    Subsystem.SYSCALLS,
                    Subsystem.NETWORK,
                    Subsystem.SYSTEM,
                }
            ),
            timeout,
        )

    def _run(
        self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int
    ) -> Iterable[TestResult]:
        stress_ng = StressNg(client)

        for params in tests:
            yield from self.run_test(
                stress_ng=stress_ng, executor=executor, timeout=timeout, **params
            )


class StressNgCombineLoadTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Test stress-ng full combine load on subsystems.",
            frozenset(
                {
                    Subsystem.MEMORY,
                    Subsystem.FILE,
                    Subsystem.IPC,
                    Subsystem.SYSCALLS,
                    Subsystem.NETWORK,
                    Subsystem.SYSTEM,
                }
            ),
            timeout,
        )

    def _run(
        self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int
    ) -> Iterable[TestResult]:
        stress_ng = StressNg(client)

        for r in range(2, len(tests)):
            for test_combination in combinations(tests, r):
                test_params = combine_params(test_combination)
                yield from self.run_test(
                    stress_ng=stress_ng, executor=executor, timeout=timeout, **test_params
                )


class StressNgParallelLoadTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Test stress-ng full parallel load on subsystems.",
            frozenset(
                {
                    Subsystem.MEMORY,
                    Subsystem.FILE,
                    Subsystem.IPC,
                    Subsystem.SYSCALLS,
                    Subsystem.NETWORK,
                    Subsystem.SYSTEM,
                }
            ),
            timeout,
        )

    def _run(
        self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int
    ) -> Iterable[TestResult]:
        stress_ng = StressNg(client)

        test_params = combine_params(tests)
        yield from self.run_test(
            stress_ng=stress_ng, executor=executor, timeout=timeout, **test_params
        )
