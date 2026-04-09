from itertools import combinations
from typing import TYPE_CHECKING, Any

from imgtests.exec.exec import common_run_command
from imgtests.exec.loaders import StressNg
from imgtests.runner import TestResult, TestStatus
from imgtests.suites.general.stress_ng import StressNgTest
from imgtests.types import Subsystem

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


def combine_params(
    test_combination: tuple[dict[str, Any], ...] | list[dict[str, Any]],
) -> dict[str, Any]:
    """Combines params into single dictionary.

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

        subtest_timeout = timeout // len(tests)
        if subtest_timeout == 0:
            err_msg = "Invalid timeout for subtests. Needs increase timeout."
            raise ValueError(err_msg)
        self.logger.info(
            "Each subtest running time: %d. Count of subtests: %s.",
            subtest_timeout,
            len(tests),
        )
        for params in tests:
            yield from self.run_test(
                stress_ng=stress_ng, executor=executor, timeout=subtest_timeout, **params
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

        test_combinations = [
            test_combination
            for r in range(2, len(tests))
            for test_combination in combinations(tests, r)
        ]
        combination_timeout = timeout // len(test_combinations)
        if combination_timeout == 0:
            err_msg = "Insufficient timeout for all combinations. Needs increase timeout."
            raise ValueError(err_msg)
        self.logger.info(
            "Each subtest running time: %d. Count of subtests: %s.",
            combination_timeout,
            len(test_combinations),
        )
        for test_combination in test_combinations:
            test_params = combine_params(test_combination)
            yield from self.run_test(
                stress_ng=stress_ng, executor=executor, timeout=combination_timeout, **test_params
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
    """Runs stress-ng IPC subsystem tests with iterational increment of stressors amount.

    Iteration begins with 1 and goes up to nprocs.

    IPC subsystem class consists:
    dekker, fifo, futex, mq, msg, peterson, pipe, pipeherd,
    sem, sem-sysv, shm, shm-sysv, sigq, sock.
    """

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

        result = common_run_command(["nproc"], client)
        if result.returncode:
            yield TestResult(status=TestStatus.BROKEN)
            return
        ipc_max = int(result.stdout)
        subtest_timeout = timeout // ipc_max
        if subtest_timeout == 0:
            err_msg = "Invalid timeout for IPC stress-ng test. Needs increase timeout."
            raise ValueError(err_msg)
        for param in range(1, ipc_max + 1):
            yield from self.run_test(
                stress_ng=stress_ng,
                executor=executor,
                timeout=subtest_timeout,
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
