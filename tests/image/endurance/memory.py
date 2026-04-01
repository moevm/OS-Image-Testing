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
    # General memory stress test with mmap() callings
    {"vm": 4, "vm_bytes": "35%", "vm_populate": True, "mmap": 4, "mmap_bytes": "35%"},
    # Memory bandwidth test
    {"memrate": 0, "memrate_rd_mbs": 500, "memrate_wr_mbs": 1000},
    # Memory mappings of various sizes and calls test
    {"mmaptorture": 0, "mmaptorture_bytes": "70%"},
]


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
        for params in tests:
            yield from self.run_test(
                stress_ng=stress_ng, executor=executor, timeout=timeout, **params
            )
