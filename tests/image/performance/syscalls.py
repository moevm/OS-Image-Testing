from datetime import datetime
from time import sleep
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from imgtests.exec.loaders import Kirk, Perf, StressNg
from imgtests.planning import AbstractRunnableTimeLimitedTest
from imgtests.suites.duration import ONE_MIN_SEC
from imgtests.suites.general.stress_ng import StressNgTest
from imgtests.types import Subsystem, TestResult, TestStatus

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


class SyscallsWithCpuLoadTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Syscalls test with cpu load scaling cpu percent from 50% to 100%.",
            frozenset({Subsystem.SYSCALLS}),
            timeout,
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        stress_ng = StressNg(client)
        kirk = Kirk(client)

        cpu_loads = (50, 60, 70, 80, 90, 100)
        subtest_timeout = timeout // len(cpu_loads)
        if subtest_timeout == 0:
            err_msg = f"Timeout '{timeout}' is too small for the number of subtests."
            raise ValueError(err_msg)
        for cpu_percent in cpu_loads:
            self.logger.info("Running test with %d cpu load...", cpu_percent)
            started_at = datetime.now(tz=ZoneInfo("UTC"))
            future_kirk = executor.submit(kirk.run, ["syscalls"], timeout=timeout)
            future_stress_ng = executor.submit(
                stress_ng.run,
                timeout_sec=timeout,
                syscall=0,
                syscall_method="all",
                cpu=0,
                cpu_method="matrixprod",
                cpu_load=cpu_percent,
            )
            kirk_res = None
            stress_ng_res = None

            while not future_stress_ng.done():
                if future_kirk.done():
                    if kirk_res is None:
                        kirk_res, kirk_metrics_path = future_kirk.result()
                    future_kirk = executor.submit(kirk.run, ["syscalls"], timeout=ONE_MIN_SEC)
                sleep(5)
            while not future_kirk.done():
                if future_stress_ng.done():
                    if stress_ng_res is None:
                        stress_ng_res, stress_ng_metrics = future_stress_ng.result()
                    future_stress_ng = executor.submit(
                        stress_ng.run,
                        timeout_sec=ONE_MIN_SEC,
                        syscall=0,
                        syscall_method="all",
                        cpu=0,
                        cpu_method="matrixprod",
                        cpu_load=cpu_percent,
                    )
                sleep(5)

            if stress_ng_res is None:
                stress_ng_res, stress_ng_metrics = future_stress_ng.result()
            if kirk_res is None:
                kirk_res, kirk_metrics_path = future_kirk.result()

            if stress_ng_res.returncode or kirk_res.returncode:
                yield TestResult(status=TestStatus.FAILED)
            else:
                yield TestResult(
                    status=TestStatus.PASSED,
                    command=" ".join(stress_ng_res.cmd) + " & " + " ".join(kirk_res.cmd),
                    metrics={
                        **stress_ng.metrics_to_json(stress_ng_metrics),
                        **kirk.metrics_to_json(kirk_metrics_path),
                    },
                    started_at=started_at,
                    ended_at=datetime.now(tz=ZoneInfo("UTC")),
                )


class StressNgSyscallsWithMemLoadTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Stress-ng syscalls test with memory load.",
            frozenset({Subsystem.SYSCALLS}),
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
            syscall=0,
            syscall_method="all",
            vm=0,
            vm_bytes="95%",
        )


class SyscallsFullLoadTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Syscalls full load test.",
            frozenset({Subsystem.SYSCALLS}),
            timeout,
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        stress_ng = StressNg(client)
        perf = Perf(client)

        started_at = datetime.now(tz=ZoneInfo("UTC"))
        future_stress_ng = executor.submit(
            stress_ng.run,
            timeout_sec=timeout,
            syscall=0,
        )
        future_perf = executor.submit(
            perf.bench,
            collection="syscall",
        )
        perf_res = None
        stress_ng_res = None

        while not future_stress_ng.done():
            if future_perf.done():
                if perf_res is None:
                    perf_res, perf_metrics = future_perf.result()
                future_perf = executor.submit(
                    perf.bench,
                    collection="syscall",
                )
            sleep(5)
        while not future_perf.done():
            if future_stress_ng.done():
                if stress_ng_res is None:
                    stress_ng_res, stress_ng_metrics = future_stress_ng.result()
                future_stress_ng = executor.submit(
                    stress_ng.run,
                    timeout_sec=ONE_MIN_SEC,
                    syscall=0,
                )
            sleep(5)

        if stress_ng_res is None:
            stress_ng_res, stress_ng_metrics = future_stress_ng.result()
        if perf_res is None:
            perf_res, perf_metrics = future_perf.result()

        if perf_res.returncode or stress_ng_res.returncode:
            yield TestResult(
                status=TestStatus.FAILED,
            )
        else:
            yield TestResult(
                status=TestStatus.PASSED,
                command=" ".join(stress_ng_res.cmd) + " & " + " ".join(perf_res.cmd),
                metrics={
                    **stress_ng.metrics_to_json(stress_ng_metrics),
                    "perf_metrics": perf.metrics_to_json(perf_metrics),
                },
                started_at=started_at,
                ended_at=datetime.now(tz=ZoneInfo("UTC")),
            )
