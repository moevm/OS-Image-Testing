import logging
import random
from datetime import datetime
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from imgtests.exec.exec import ExecResult, pipeline
from imgtests.exec.loaders import StressNg
from imgtests.exec.observers import Sar
from imgtests.runner import AbstractRunnableTimeLimitedTest, Subsystem, TestResult
from imgtests.suites.general.stress_ng import StressNgTest

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient

logger = logging.getLogger(__name__)

PAGE_SIZE = 4  # kB
HUGE_PAGE_SIZE = 2048  # kB

tests: list[dict[str, Any]] = [
    {"vm": 4, "vm_bytes": "25%", "mmap": 4, "mmap_bytes": "25%"},
    {"vm": 4, "vm_bytes": "35%", "mmap": 4, "mmap_bytes": "35%"},
    {"vm": 1024, "vm_bytes": "16M"},
    {"vm": 1024, "vm_bytes": "1G"},
]


def get_ram_size(client: SSHClient | None = None) -> ExecResult:
    commands = [
        ["grep", "MemTotal", "/proc/meminfo"],
        ["awk", "'{print $2}'"],
    ]
    for result in pipeline(cmds=commands, ssh_client=client, pass_output=True):
        last_result = result
        if result.returncode:
            logger.error("Find RAM size failed: '%s'", result.stderr)
            return result
    return last_result


class StressNgPerformanceVMTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__("Stress-ng performance VM test.", frozenset({Subsystem.MEMORY}), timeout)

    def _run(
        self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int
    ) -> Iterable[TestResult]:
        result = get_ram_size(client=client)
        if result.returncode:
            return
        ram_size = int(result.stdout)

        stress_ng = StressNg(client)
        for params in tests:
            yield from self.run_test(
                stress_ng=stress_ng, executor=executor, timeout=timeout, **params
            )

        workers = 512 if ram_size < (1024 * HUGE_PAGE_SIZE) else 1024
        yield from self.run_test(
            stress_ng=stress_ng, executor=executor, timeout=timeout, mmaphuge=workers
        )

        instances = int((ram_size * 0.7) / (HUGE_PAGE_SIZE * random.uniform(1, 2)))  # noqa: S311
        instances = min(instances, 1024)
        yield from self.run_test(
            stress_ng=stress_ng, executor=executor, timeout=timeout, vm=instances, vm_bytes="70%"
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
