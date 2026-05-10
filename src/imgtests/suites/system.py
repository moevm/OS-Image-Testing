from datetime import UTC, datetime
from time import sleep
from typing import TYPE_CHECKING

from imgtests.exec.loaders import Chaosblade, PhoronixTestSuite, StressNg
from imgtests.exec.observers.systemd_analyze import SystemdAnalyze
from imgtests.planning import AbstractRunnableManyTimesTest, AbstractRunnableTimeLimitedTest
from imgtests.suites.general.stress_ng import StressNgTest
from imgtests.types import Subsystem, TestResult, TestStatus

if TYPE_CHECKING:
    import logging
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


class SystemLoadTimeTest(AbstractRunnableManyTimesTest):
    def __init__(self) -> None:
        super().__init__("System load time.", frozenset({Subsystem.SYSTEM}))

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        iterations: int,  # noqa: ARG002
    ) -> Iterable[TestResult]:
        systemd_analyze = SystemdAnalyze(client)
        result = systemd_analyze.time()
        sleep_time_sec = 10
        wait_timeout_sec = 600
        while result.total_time < 0 and wait_timeout_sec > 0:
            self.logger.info(
                "Waiting for system to be ready to analyze boot time, %d seconds left.",
                wait_timeout_sec,
            )
            sleep(sleep_time_sec)
            wait_timeout_sec -= sleep_time_sec
            result = systemd_analyze.time()
        if result.total_time < 0:
            self.logger.error("Failed to get boot time, system might not be ready.")
        yield TestResult(
            command=f"{systemd_analyze.name} time",
            metrics=result._asdict(),
            status=TestStatus.PASSED,
        )

    def cleanup(self, client: SSHClient | None, logger: logging.Logger) -> None:  # noqa: ARG002
        logger.debug("Noting to cleanup for system load time test.")


class SystemSlowServicesTest(AbstractRunnableManyTimesTest):
    def __init__(self) -> None:
        super().__init__("System slow services.", frozenset({Subsystem.SYSTEM}))

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        iterations: int,  # noqa: ARG002
    ) -> Iterable[TestResult]:
        systemd_analyze = SystemdAnalyze(client)
        result = SystemdAnalyze.metrics_to_json(systemd_analyze.slow_load_services())
        yield TestResult(
            command=f"{systemd_analyze.name} critical-chain",
            metrics=result,
            status=TestStatus.PASSED,
        )

    def cleanup(self, client: SSHClient | None, logger: logging.Logger) -> None:  # noqa: ARG002
        logger.debug("Noting to cleanup for system slow services test.")


class PTSSystemTest(AbstractRunnableManyTimesTest):
    def __init__(self, iterations: int = 1) -> None:
        super().__init__("Load system with PTS.", frozenset({Subsystem.SYSTEM}), iterations)

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        iterations: int,
    ) -> Iterable[TestResult]:
        pts = PhoronixTestSuite(client)
        future = executor.submit(pts.prepare)
        result = future.result()
        if result.returncode:
            self.logger.error("PTS setup failed: '%s'", result.stderr)
            return TestResult(status=TestStatus.BROKEN)

        for test_name in ("pts/ctx-clock", "pts/appleseed"):
            started_at = datetime.now(UTC)
            future = executor.submit(pts.run, test_name=test_name, run_count=iterations)
            result, metrics = future.result()
            if pts.is_timeout_result(result):
                self.logger.error("PTS test '%s' timed out.", test_name)
                yield TestResult(status=TestStatus.BROKEN)
            elif result.returncode:
                self.logger.error("PTS test '%s' FAILED.", test_name)
                yield TestResult(status=TestStatus.FAILED)
            else:
                metrics = PhoronixTestSuite.split_result(raw_metrics=metrics)
                yield TestResult(
                    command=" ".join(result.cmd),
                    metrics=metrics,
                    started_at=started_at,
                    status=TestStatus.PASSED,
                )


class StressNgEnduranceCpuTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Stress-ng endurance CPU test.",
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
        started_at = datetime.now(UTC)
        future = executor.submit(chaos.create_cpu_exp, cpu_percent=70, timeout_sec=timeout)
        result, chaos_result = future.result()
        # actually wait till the experiment is completed
        if chaos_result.success and isinstance(chaos_result.result, str):
            future = executor.submit(
                chaos.await_exp_result,
                experiment_id=chaos_result.result,
                timeout=timeout,
            )
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
