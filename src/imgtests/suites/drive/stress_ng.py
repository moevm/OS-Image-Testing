from typing import TYPE_CHECKING

from imgtests.exec.loaders import StressNg
from imgtests.planning.base import calc_subtest_timeout
from imgtests.suites.general.stress_ng import StressNgTest
from imgtests.types import Subsystem

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient
    from imgtests.types import TestResult


class StressNgEnduranceFileTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Stress-ng endurance filesystem test.",
            frozenset({Subsystem.FILE}),
            timeout,
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        stress_ng = StressNg(client)
        hdd_bytes_percents = tuple(range(50, 100, 10))
        subtest_timeout = calc_subtest_timeout(timeout, len(hdd_bytes_percents))
        for usage in hdd_bytes_percents:
            yield from self.run_test(
                stress_ng=stress_ng,
                executor=executor,
                timeout=subtest_timeout,
                hdd=0,
                hdd_bytes=f"{usage}%",
                hdd_opts="sync",
            )
