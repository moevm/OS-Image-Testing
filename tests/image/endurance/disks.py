from typing import TYPE_CHECKING

from imgtests.exec.loaders import StressNg
from imgtests.suites.general.stress_ng import StressNgTest
from imgtests.types import Subsystem

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient
    from imgtests.types import TestResult


class StressNgEnduranceDisksTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Stress-ng endurance disks test.",
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
        yield from self.run_test(
            stress_ng=stress_ng,
            executor=executor,
            timeout=timeout,
            hdd=1,
            hdd_bytes="100M",
            hdd_opts="sync",
        )
