import logging
import random
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from imgtests.exec.loaders import StressNg
from imgtests.exec.observers import Sar
from imgtests.exec.observers.resource import get_total_ram_size
from imgtests.planning import AbstractRunnableTimeLimitedTest
from imgtests.suites.general.stress_ng import StressNgTest
from imgtests.types import Subsystem, TestResult, TestStatus

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient

logger = logging.getLogger(__name__)


HUGE_PAGE_SIZE_KIB = 2048
STRESSORS_LIMIT = 1024
RAM_LOAD = 0.7

tests: list[dict[str, Any]] = [
    # General memory stress test with mmap() callings
    {"vm": 4, "vm_bytes": "35%", "vm_populate": True, "mmap": 4, "mmap_bytes": "35%"},
    # Memory bandwidth test
    {"memrate": 0, "memrate_rd_mbs": 500, "memrate_wr_mbs": 1000},
    # Memory mappings of various sizes and calls test
    {"mmaptorture": 0, "mmaptorture_bytes": "70%"},
]
perf_tests: list[dict[str, Any]] = [
    # 50% and 70% RAM load tests
    {"vm": 4, "vm_bytes": "25%", "mmap": 4, "mmap_bytes": "25%"},
    {"vm": 4, "vm_bytes": "35%", "mmap": 4, "mmap_bytes": "35%"},
    # Fixed allocation size per instance tests
    {"vm": 1024, "vm_bytes": "4M"},  # 4 KiB each (4096 KiB / 1024), equal to page size
    {"vm": 1024, "vm_bytes": "1G"},  # 1 MiB each (1024 MiB / 1024), between page and huge page size
]


class StressNgEnduranceMemoryTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Stress-ng endurance memory test.",
            frozenset({Subsystem.MEMORY}),
            timeout,
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        stress_ng = StressNg(client)
        for params in tests:
            yield from self.run_test(
                stress_ng=stress_ng,
                executor=executor,
                timeout=timeout,
                **params,
            )


class StressNgPerformanceMemoryTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Sequential performance memory test with stress-ng.",
            frozenset({Subsystem.MEMORY}),
            timeout,
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        ram_size = get_total_ram_size(client=client)
        if ram_size is None:
            yield TestResult(status=TestStatus.BROKEN)
            return

        stress_ng = StressNg(client)

        workers = (
            STRESSORS_LIMIT // 2
            if ram_size < (STRESSORS_LIMIT * HUGE_PAGE_SIZE_KIB)
            else STRESSORS_LIMIT
        )
        instances = int((ram_size * RAM_LOAD) / (HUGE_PAGE_SIZE_KIB * random.uniform(1, 2)))  # noqa: S311
        instances = min(instances, STRESSORS_LIMIT)

        # Test with huge pages
        perf_tests.append({"mmaphuge": workers})

        # Randomized test with allocation per instance above huge page size
        perf_tests.append({"vm": instances, "vm_bytes": "70%"})

        for params in perf_tests:
            yield from self.run_test(
                stress_ng=stress_ng,
                executor=executor,
                timeout=timeout,
                **params,
            )


class SarWithStressNGTest(AbstractRunnableTimeLimitedTest):
    """Tests that run stress-ng with sar to measure pgscan time."""

    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Stress-ng with sar measure pgscan time.",
            frozenset({Subsystem.MEMORY}),
            timeout,
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        sar = Sar(client)

        stress_ng = StressNg(client)
        started_at = datetime.now(UTC)
        stress_ng_future = executor.submit(
            stress_ng.run,
            timeout_sec=timeout,
            vm=4,
            vm_bytes="95%",
        )

        _, pgscan = sar.run(interval=1, count=timeout)
        result, metrics = stress_ng_future.result()
        if result.returncode:
            yield TestResult(status=TestStatus.FAILED)
        else:
            metrics_json = stress_ng.metrics_to_json(metrics)
            yield TestResult(
                status=TestStatus.PASSED,
                metrics={
                    "pgscan_time_sec": pgscan,
                    **metrics_json,
                },
                command=" ".join(result.cmd),
                started_at=started_at,
            )
