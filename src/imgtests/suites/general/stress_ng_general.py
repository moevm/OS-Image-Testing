from itertools import combinations
from typing import TYPE_CHECKING, Any

from imgtests.exec.loaders import StressNg
from imgtests.planning.base import calc_subtest_timeout
from imgtests.suites.general.stress_ng import StressNgTest
from imgtests.types import Subsystem, TestResult

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
                },
            ),
            timeout,
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        stress_ng = StressNg(client)

        subtest_timeout = calc_subtest_timeout(timeout, len(tests))
        self.logger.info(
            "Each subtest running time: %d. Count of subtests: %s.",
            subtest_timeout,
            len(tests),
        )
        for params in tests:
            yield from self.run_test(
                stress_ng=stress_ng,
                executor=executor,
                timeout=subtest_timeout,
                **params,
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
                },
            ),
            timeout,
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        stress_ng = StressNg(client)

        test_combinations = [
            test_combination
            for r in range(2, len(tests))
            for test_combination in combinations(tests, r)
        ]
        combination_timeout = calc_subtest_timeout(timeout, len(test_combinations))
        self.logger.info(
            "Each subtest running time: %d. Count of subtests: %s.",
            combination_timeout,
            len(test_combinations),
        )
        for test_combination in test_combinations:
            test_params = combine_params(test_combination)
            yield from self.run_test(
                stress_ng=stress_ng,
                executor=executor,
                timeout=combination_timeout,
                **test_params,
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
                },
            ),
            timeout,
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        stress_ng = StressNg(client)

        test_params = combine_params(tests)
        yield from self.run_test(
            stress_ng=stress_ng,
            executor=executor,
            timeout=timeout,
            **test_params,
        )
