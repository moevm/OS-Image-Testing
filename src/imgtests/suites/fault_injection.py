import logging
import random
from datetime import UTC, datetime
from time import sleep
from typing import TYPE_CHECKING

from imgtests.exec.debugfs import change_fault_parameters
from imgtests.exec.exec import ExecResult, SSHClient
from imgtests.exec.loaders import Chaosblade, ChaosResponse, Kirk, Perf, StressNg
from imgtests.exec.osinfo import get_os_release
from imgtests.exec.user_commands import MkDir
from imgtests.planning import AbstractRunnableTimeLimitedTest, calc_subtest_timeout
from imgtests.suites.drive.fio import FIO_RESULTS_DIR, FioSuite, FioSuiteConfig, FioWorkload
from imgtests.types import Distro, Subsystem, TestResult, TestStatus

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import Future, ThreadPoolExecutor

    from imgtests.exec.exec import ExecResult, SSHClient


logger = logging.getLogger(__name__)


class FaultCleanupMixin:
    def cleanup(self, client: SSHClient | None, logger: logging.Logger) -> None:
        change_fault_parameters(client, 0, 1)
        logger.info("Cleaned fault parameters.")
        default_cleanup = getattr(super(), "cleanup", None)
        if default_cleanup:
            default_cleanup(client, logger)


class FaultInjectionEnduranceTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int, iterations: int = 4) -> None:
        super().__init__(
            "Endurance test with periodic fault injection.",
            frozenset({Subsystem.FILE, Subsystem.SYSTEM}),
            timeout,
        )
        self.iterations = iterations

    @property
    def kirk_suites(self) -> tuple[str, ...]:
        return ("syscalls", "fs", "mm", "dio")

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        if not is_fault_injection_available(client):
            self.logger.warning("Skipping test due to fault injection is supported on poky.")
            return TestResult(status=TestStatus.SKIPPED)

        kirk = Kirk(client)
        if not kirk.is_suites_available(self.kirk_suites):
            self.logger.warning("Kirk suite not available for the image with LTP.")
            return TestResult(status=TestStatus.SKIPPED)

        random.seed(timeout)
        fault_probabilities = [
            random.randint(30, 80) if i % 2 == 1 else 0  # noqa: S311
            for i in range(self.iterations)
        ]
        time_per_test = (timeout // self.iterations) + 1

        for fault_probability in fault_probabilities:
            started_at = datetime.now(UTC)
            result, metrics_path = kirk.run(
                scenarios=self.kirk_suites,
                timeout=time_per_test,
                fault_prob=fault_probability,
                fault_interval=10,
            )

            if metrics_path:
                yield TestResult(
                    command=" ".join(result.cmd),
                    metrics=kirk.metrics_to_json(metrics_path),
                    started_at=started_at,
                    status=TestStatus.PASSED,
                )
            else:
                yield TestResult(
                    command=" ".join(result.cmd),
                    started_at=started_at,
                    status=TestStatus.FAILED,
                )


class FaultInjectionChaosbladeTest(FaultCleanupMixin, AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Chaosblade test with fault injection.",
            frozenset({Subsystem.FILE, Subsystem.SYSTEM}),
            timeout,
        )

    @property
    def chaosblade_suites(self) -> tuple[str, str]:
        return ("create_disk_exp", "create_cpu_exp")

    @property
    def fault_probs(self) -> tuple[int, ...]:
        return (0, 50, 70, 90, 95)

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        if not is_fault_injection_available(client):
            self.logger.warning("Skipping test due to fault injection is supported on poky.")
            return TestResult(status=TestStatus.SKIPPED)
        tmp_dir = "/var/tmp/chaos-fault-injection"  # noqa: S108
        mkdir = MkDir(client)
        mkdir([tmp_dir])
        timeout_suite = calc_subtest_timeout(
            timeout,
            len(self.chaosblade_suites) * len(self.fault_probs),
            60,
        )
        chaosblade = Chaosblade(client)
        for fault_prob in self.fault_probs:
            self.logger.info("Run with %d fault_prob and %d timeout", fault_prob, timeout_suite)
            for chaosblade_suite in self.chaosblade_suites:
                started_at = datetime.now(UTC)
                result = change_fault_parameters(client, fault_prob, 5)
                if result.returncode:
                    yield TestResult(
                        command=" ".join(result.cmd),
                        started_at=started_at,
                        status=TestStatus.FAILED,
                    )
                    return

                chaosblade_future = self._create_chaosblade_future(
                    executor,
                    chaosblade,
                    chaosblade_suite,
                    tmp_dir,
                    timeout_suite,
                )
                result, chaosblade_result = chaosblade_future.result()
                status = TestStatus.PASSED

                if chaosblade_result.success and isinstance(chaosblade_result.result, str):
                    future = executor.submit(
                        chaosblade.await_exp_result,
                        chaosblade_result.result,
                    )
                    while not future.done():
                        _, chaosblade_status = chaosblade.get_exp_status(
                            chaosblade_result.result,
                        )
                        if chaosblade_status.result["Status"] == "Error":
                            status = TestStatus.FAILED
                            break
                        sleep(1)
                    future.result()
                else:
                    status = TestStatus.FAILED
                yield TestResult(
                    metrics=chaosblade_result,
                    command=" ".join(result.cmd),
                    started_at=started_at,
                    status=status,
                )

    def _create_chaosblade_future(
        self,
        executor: ThreadPoolExecutor,
        chaosblade: Chaosblade,
        chaosblade_suite: str,
        tmp_dir: str,
        timeout_suite: int,
    ) -> Future[tuple[ExecResult, ChaosResponse]]:
        match chaosblade_suite:
            case "create_disk_exp":
                return executor.submit(
                    chaosblade.create_disk_exp,
                    action="fill",
                    percent=25,
                    path=tmp_dir,
                    timeout_sec=timeout_suite,
                )
            case "create_cpu_exp":
                return executor.submit(
                    chaosblade.create_cpu_exp,
                    cpu_percent=10,
                    timeout_sec=timeout_suite,
                )
            case _:
                err_msg = "Unknown chaosblade method."
                raise ValueError(err_msg)


class FaultInjectionStressNgTest(FaultCleanupMixin, AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Stress-ng test with fault injection.",
            frozenset({Subsystem.MEMORY, Subsystem.SYSTEM}),
            timeout,
        )

    @property
    def stress_ng_suites(self) -> tuple[dict[str, str | int], dict[str, str | int]]:
        return (
            {"vm": 4, "vm_bytes": "35%", "mmap": 4, "mmap_bytes": "35%"},
            {"syscall": 0},
        )

    @property
    def fault_probs(self) -> tuple[int, ...]:
        return (0, 50, 70, 90)

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        if not is_fault_injection_available(client):
            self.logger.warning("Skipping test due to fault injection is supported on poky.")
            return TestResult(status=TestStatus.SKIPPED)

        stress_ng = StressNg(client)
        timeout_suite = (timeout // (len(self.stress_ng_suites) * len(self.fault_probs))) + 1
        for fault_prob in self.fault_probs:
            self.logger.info("Run with %d fault_prob and %d timeout", fault_prob, timeout_suite)
            for stress_ng_suite in self.stress_ng_suites:
                started_at = datetime.now(UTC)
                result = change_fault_parameters(client, fault_prob, 5)
                if result.returncode:
                    yield TestResult(
                        command=" ".join(result.cmd),
                        started_at=started_at,
                        status=TestStatus.FAILED,
                    )
                    return

                stress_ng_future = executor.submit(
                    stress_ng.run,
                    timeout=timeout_suite,
                    **stress_ng_suite,
                )
                result, metrics = stress_ng_future.result()

                if result.returncode == stress_ng.INCORRECT_OPT_OR_FATAL_ISSUE_CODE:
                    self.logger.error("stress-ng test BROKEN")
                    yield TestResult(status=TestStatus.BROKEN)
                    return
                elif result.returncode:
                    self.logger.error("stress-ng test FAILED")
                    yield TestResult(status=TestStatus.FAILED)
                    return

                yield TestResult(
                    metrics=stress_ng.metrics_to_json(metrics),
                    command=" ".join(result.cmd),
                    started_at=started_at,
                    status=TestStatus.PASSED,
                )


class FaultInjectionPerfTest(FaultCleanupMixin, AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Perf bench test with fault injection.",
            frozenset({Subsystem.SYSCALLS, Subsystem.IPC}),
            timeout,
        )

    @property
    def perf_suites(self) -> tuple[str, str]:
        return ("sched", "syscall")

    @property
    def fault_probs(self) -> tuple[int, ...]:
        return (0, 50, 70, 90)

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        if not is_fault_injection_available(client):
            self.logger.warning("Skipping test due to fault injection is supported on poky.")
            return TestResult(status=TestStatus.SKIPPED)

        perf = Perf(client)
        timeout_suite = (timeout // (len(self.perf_suites) * len(self.fault_probs))) + 1
        for fault_prob in self.fault_probs:
            self.logger.info("Run with %d fault_prob and %d timeout", fault_prob, timeout_suite)
            for perf_suite in self.perf_suites:
                started_at = datetime.now(UTC)
                result = change_fault_parameters(client, fault_prob, 5)
                if result.returncode:
                    yield TestResult(
                        command=" ".join(result.cmd),
                        started_at=started_at,
                        status=TestStatus.FAILED,
                    )
                    return

                perf_future = executor.submit(
                    perf.bench,
                    collection=perf_suite,
                )

                result, perf_metrics = perf_future.result()
                if result.returncode:
                    yield TestResult(
                        command=" ".join(result.cmd),
                        started_at=started_at,
                        status=TestStatus.FAILED,
                    )
                elif perf_metrics:
                    yield TestResult(
                        command=" ".join(result.cmd),
                        metrics=perf.metrics_to_json(perf_metrics),
                        started_at=started_at,
                        status=TestStatus.PASSED,
                    )


class FaultInjectionFioTest(FaultCleanupMixin, AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Fio test with fault injection.",
            frozenset({Subsystem.FILE}),
            timeout,
        )

    @property
    def fio_suites(self) -> tuple[FioWorkload, ...]:
        return (
            FioWorkload("seq_write_1M", "write", "1M", 1.0),
            FioWorkload("seq_read_64k", "read", "64k", 1.0),
        )

    @property
    def fault_probs(self) -> tuple[int, ...]:
        return (0, 50, 70, 90)

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        if not is_fault_injection_available(client):
            self.logger.warning("Skipping test due to fault injection is supported on poky.")
            return TestResult(status=TestStatus.SKIPPED)

        timeout_suite = (timeout // (len(self.fio_suites) * len(self.fault_probs))) + 1
        for fault_prob in self.fault_probs:
            self.logger.info("Run with %d fault_prob and %d timeout", fault_prob, timeout_suite)
            for fio_suite in self.fio_suites:
                started_at = datetime.now(UTC)
                result = change_fault_parameters(client, fault_prob, 5)
                if result.returncode:
                    yield TestResult(
                        command=" ".join(result.cmd),
                        started_at=started_at,
                        status=TestStatus.FAILED,
                    )
                    return

                fio_config = FioSuiteConfig(
                    suite="fault_injection",
                    duration_sec=timeout_suite,
                    results_dir=FIO_RESULTS_DIR,
                    workloads=(fio_suite,),
                )

                fio = FioSuite(client, fio_config).run()
                yield from fio


def is_fault_injection_available(client: SSHClient | None) -> bool:
    os_id = get_os_release(client).id
    return not (os_id and os_id != Distro.POKY.value)
