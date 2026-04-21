from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from imgtests.exec.loaders import Chaosblade, StressNg
from imgtests.runner import AbstractRunnableTimeLimitedTest, TestResult, TestStatus
from imgtests.suites.general.stress_ng import StressNgTest
from imgtests.types import Subsystem

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


class StressNgPerformanceCpuTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Stress-ng performance CPU test.",
            frozenset({Subsystem.SYSTEM}),
            timeout,
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        stress_ng = StressNg(client)
        yield from self.run_test(stress_ng=stress_ng, executor=executor, timeout=timeout, cpu=0)


class ChaosbladeCPUTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__("Load CPU 70% with chaosblade.", frozenset({Subsystem.SYSTEM}), timeout)

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        chaos = Chaosblade(client)
        started_at = datetime.now(tz=ZoneInfo("UTC"))
        future = executor.submit(chaos.create_cpu_exp, cpu_percent=70, timeout_sec=timeout)
        result, chaos_result = future.result()
        # actually wait till the experiment is completed
        if chaos_result.success:
            future = executor.submit(chaos.await_exp_result, experiment_id=chaos_result.result)
            result, chaos_result = future.result()
            if result.returncode:
                status = TestStatus.BROKEN
            else:
                status = TestStatus.PASSED if chaos_result.success else TestStatus.FAILED
        else:
            status = TestStatus.BROKEN
        yield TestResult(
            metrics=chaos_result,
            command=" ".join(result.cmd),
            started_at=started_at,
            status=status,
        )
