from itertools import combinations
from typing import TYPE_CHECKING, Any

from imgtests.exec.loaders import StressNg
from imgtests.suites.general.stress_ng import StressNgTest
from imgtests.types import Subsystem

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient
    from imgtests.runner import TestResult


tests: list[dict[str, Any]] = [
    {"cpu": 0, "cpu_method": "matrixprod"},
    {"vm": 3, "vm_bytes": "2G", "mmap": 3, "mmap_bytes": "2G"},
    {"hdd": 0, "hdd_bytes": "2G"},
    {"sock": 2, "netdev": 2, "udp_flood": 2},
    {"syscall": 0},
    {"mq": 4, "pipe": 4, "sem": 4, "shm": 4},
]
IPC_MAX = 16


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


class StressNgIterTestIPC(StressNgTest):
    """Runs stress-ng IPC subsystem tests via --class ipc with iterational
    incrementation of stressors amount.

    Iteration begins with 1 and goes up to
    magically defined number of IPC_MAX.

    IPC subsystem class consists:
    dekker, fifo, futex, mq, msg, peterson, pipe, pipeherd,
    sem, sem-sysv, shm, shm-sysv, sigq, sock.
    """  # noqa: D205

    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Test stress-ng iterational IPC subsystem test.",
            frozenset({Subsystem.IPC}),
            timeout,
        )

    def _run(
        self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int
    ) -> Iterable[TestResult]:
        stress_ng = StressNg(client)

        for param in range(1, IPC_MAX + 1):
            test_params = dict(  # noqa: C408
                dekker=param,
                fifo=param,
                futex=param,
                mq=param,
                msg=param,
                peterson=param,
                pipe=param,
                pipeherd=param,
                sem=param,
                sem_sysv=param,
                shm=param,
                shm_sysv=param,
                sigq=param,
                sock=param,
            )
            yield from self.run_test(
                stress_ng=stress_ng, executor=executor, timeout=timeout, **test_params
            )
