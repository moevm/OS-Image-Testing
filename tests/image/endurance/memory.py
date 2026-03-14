from typing import TYPE_CHECKING

from imgtests.exec.loaders import StressNg
from imgtests.runner import Subsystem, TestResult
from imgtests.suites.general.stress_ng import StressNgTest

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


class StressNgEnduranceMemoryTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Stress-ng endurance memory test.",
            frozenset({Subsystem.MEMORY}),
            timeout,
        )

    def _run(
        self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int
    ) -> Iterable[TestResult]:
        stress_ng = StressNg(client)
        yield from self.run_test(
            stress_ng=stress_ng,
            executor=executor,
            timeout=timeout,
            vm=2,
            vm_bytes="16M",
        )
