import logging
import random
from datetime import datetime
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from imgtests.exec.exec import common_run_command
from imgtests.exec.loaders import StressNg
from imgtests.exec.observers import Sar
from imgtests.runner import AbstractRunnableTimeLimitedTest, Subsystem, TestResult
from imgtests.suites.general.stress_ng import StressNgTest

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient

logger = logging.getLogger(__name__)

HUGE_PAGE_SIZE = 2048  # Kb
STRESSORS_LIMIT = 1024
RAM_LOAD = 0.7

tests: list[dict[str, Any]] = [
    # 50% and 70% RAM load tests
    {"vm": 4, "vm_bytes": "25%", "mmap": 4, "mmap_bytes": "25%"},
    {"vm": 4, "vm_bytes": "35%", "mmap": 4, "mmap_bytes": "35%"},
    # Fixed allocation size per instance tests
    {"vm": 1024, "vm_bytes": "4M"},  # 4Kb each, equal to page size
    {"vm": 1024, "vm_bytes": "1G"},  # 1Mb each, between page and huge page size
]


def get_ram_size(client: SSHClient | None = None) -> int | None:
    result = common_run_command(["grep", "MemTotal", "/proc/meminfo"], ssh_client=client)
    if result.returncode:
        logger.error("Finding RAM size failed: '%s'", result.stderr)
        return None
    return int(result.stdout.split()[1])


class StressNgPerformanceMemoryTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Stress-ng performance memory test.", frozenset({Subsystem.MEMORY}), timeout
        )

    def _run(
        self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int
    ) -> Iterable[TestResult]:
        ram_size = get_ram_size(client=client)
        if ram_size is None:
            return

        stress_ng = StressNg(client)

        workers = (
            STRESSORS_LIMIT // 2
            if ram_size < (STRESSORS_LIMIT * HUGE_PAGE_SIZE)
            else STRESSORS_LIMIT
        )
        instances = int((ram_size * RAM_LOAD) / (HUGE_PAGE_SIZE * random.uniform(1, 2)))  # noqa: S311
        instances = min(instances, STRESSORS_LIMIT)

        # Test with huge pages
        tests.append({"mmaphuge": workers})

        # Randomized test with allocation per instance above huge page size
        tests.append({"vm": instances, "vm_bytes": "70%"})

        for params in tests:
            yield from self.run_test(
                stress_ng=stress_ng, executor=executor, timeout=timeout, **params
            )


class SarWithStressNGTest(AbstractRunnableTimeLimitedTest):
    """Tests that run stress-ng with sar to measure pgscan time."""

    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Stress-ng with sar measure pgscan time.", frozenset({Subsystem.MEMORY}), timeout
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        sar = Sar(client)

        stress_ng = StressNg(client)
        started_at = datetime.now(tz=ZoneInfo("UTC"))
        stress_ng_future = executor.submit(
            stress_ng.run,
            timeout_sec=timeout,
            vm=4,
            vm_bytes="95%",
        )

        _, pgscan = sar.run(interval=1, count=timeout)
        result, metrics = stress_ng_future.result()
        metrics_json = stress_ng.metrics_to_json(metrics)

        yield TestResult(
            metrics={
                "pgscan_time_sec": pgscan,
                **metrics_json,
            },
            command=" ".join(result.cmd),
            started_at=started_at,
        )
