from datetime import UTC, datetime
from typing import TYPE_CHECKING

from imgtests.exec.loaders import Vdbench
from imgtests.planning.base import AbstractRunnableTimeLimitedTest
from imgtests.types import Subsystem, TestResult, TestStatus

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


class VdbenchTest(AbstractRunnableTimeLimitedTest):
    """Test that runs vdbench on a disk."""

    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Load drives with vdbench.",
            frozenset({Subsystem.FILE}),
            timeout=timeout,
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        vdbench = Vdbench(client)
        started_at = datetime.now(UTC)
        future = executor.submit(vdbench.run, timeout_sec=timeout, block_size=4096, read_percentage=70, iorate=1000)
        result, output_dir = future.result()
        yield TestResult(
            metrics={"output_dir": output_dir},
            command=" ".join(result.cmd),
            started_at=started_at,
            status=TestStatus.PASSED if not result.returncode else TestStatus.FAILED,
        )
