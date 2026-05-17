import random
from datetime import UTC, datetime
from pathlib import Path
from time import sleep
from typing import TYPE_CHECKING

from imgtests.exec.loaders import Chaosblade, ChaosResponse, Kirk, Perf, StressNg
from imgtests.exec.osinfo import get_os_release
from imgtests.exec.user_commands import MkDir
from imgtests.planning import AbstractRunnableTimeLimitedTest
from imgtests.suites.drive.fio import FioSuite, FioSuiteConfig, FioWorkload
from imgtests.types import Distro, Subsystem, TestResult, TestStatus

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import Future, ThreadPoolExecutor

    from imgtests.exec.exec import ExecResult, SSHClient


class FaultInjectionEnduranceTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int, iterations: int = 4) -> None:
        super().__init__(
            "Endurance test with periodic fault injection.",
            frozenset({Subsystem.FILE, Subsystem.SYSTEM}),
            timeout,
        )
        self.iterations = iterations

    @property
    def kirk_suites(self) -> tuple[str, str]:
        return ("syscalls", "fs", "mm", "dio")

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        if not validate_fault_injection(client):
            self.logger.warning("Skipping test due to fault injection is supported on poky.")
            return TestResult(status=TestStatus.SKIPPED)

        kirk = Kirk(client)
        if not validate_kirk_suites(kirk, self.kirk_suites):
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
                scenarios=[kirk.suites],
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


class FaultInjectionChaosbladeTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Chaosblade test with fault injection.",
            frozenset({Subsystem.FILE, Subsystem.SYSTEM}),
            timeout,
        )

    @property
    def kirk_suites(self) -> tuple[str, str]:
        return ("dio", "sched")

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
        if not validate_fault_injection(client):
            self.logger.warning("Skipping test due to fault injection is supported on poky.")
            return TestResult(status=TestStatus.SKIPPED)
        tmp_dir = "/var/tmp/chaos-fault-injection"  # noqa: S108
        mkdir = MkDir(client)
        mkdir([tmp_dir])
        self._validate_timeout(timeout)
        timeout_suite = timeout // (len(self.kirk_suites) * len(self.fault_probs))
        chaosblade = Chaosblade(client)
        kirk = Kirk(client)
        if not validate_kirk_suites(kirk, self.kirk_suites):
            self.logger.warning("Kirk suite not available for the image with LTP.")
            return TestResult(status=TestStatus.SKIPPED)
        for fault_prob in self.fault_probs:
            self.logger.info("Run with %d fault_prob and %d timeout", fault_prob, timeout_suite)
            for kirk_suite, chaosblade_suite in zip(
                self.kirk_suites,
                self.chaosblade_suites,
                strict=True,
            ):
                started_at = datetime.now(UTC)
                kirk_future = executor.submit(
                    kirk.run,
                    scenarios=[kirk_suite],
                    timeout=timeout_suite,
                    fault_prob=fault_prob,
                    fault_interval=5,
                )
                sleep(1)

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
                        _, chaosblade_status = chaosblade.get_exp_status(chaosblade_result.result)
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

                result, metrics_path = kirk_future.result()
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

    def _validate_timeout(self, timeout: float) -> None:
        min_timeout = len(self.kirk_suites) * len(self.fault_probs) * 60
        if min_timeout > timeout:
            err_msg = f"The timeout is insufficient for the test. Requires at least {min_timeout}"
            raise ValueError(err_msg)

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


class FaultInjectionStressNgTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Stress-ng test with fault injection.",
            frozenset({Subsystem.MEMORY, Subsystem.SYSTEM}),
            timeout,
        )

    @property
    def kirk_suites(self) -> tuple[str, str]:
        return ("dio", "syscalls")

    @property
    def stress_ng_suites(self) -> tuple[str, str]:
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
        if not validate_fault_injection(client):
            self.logger.warning("Skipping test due to fault injection is supported on poky.")
            return TestResult(status=TestStatus.SKIPPED)

        kirk = Kirk(client)
        if not validate_kirk_suites(kirk, self.kirk_suites):
            self.logger.warning("Kirk suite not available for the image with LTP.")
            return TestResult(status=TestStatus.SKIPPED)

        stress_ng = StressNg(client)
        timeout_suite = 1 + timeout // (len(self.kirk_suites) * len(self.fault_probs))

        for fault_prob in self.fault_probs:
            self.logger.info("Run with %d fault_prob and %d timeout", fault_prob, timeout_suite)
            for kirk_suite, stress_ng_suite in zip(
                self.kirk_suites,
                self.stress_ng_suites,
                strict=True,
            ):
                started_at = datetime.now(UTC)
                kirk_future = executor.submit(
                    kirk.run,
                    scenarios=[kirk_suite],
                    timeout=timeout_suite,
                    fault_prob=fault_prob,
                    fault_interval=5,
                )
                sleep(1)

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

                result, metrics_path = kirk_future.result()
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


class FaultInjectionPerfTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Perf bench test with fault injection.",
            frozenset({Subsystem.SYSCALLS, Subsystem.IPC}),
            timeout,
        )

    @property
    def kirk_suites(self) -> tuple[str, str]:
        return ("dio", "syscalls")

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
        if not validate_fault_injection(client):
            self.logger.warning("Skipping test due to fault injection is supported on poky.")
            return TestResult(status=TestStatus.SKIPPED)

        kirk = Kirk(client)
        if not validate_kirk_suites(kirk, self.kirk_suites):
            self.logger.warning("Kirk suite not available for the image with LTP.")
            return TestResult(status=TestStatus.SKIPPED)

        perf = Perf(client)
        timeout_suite = 1 + timeout // (len(self.kirk_suites) * len(self.fault_probs))

        for fault_prob in self.fault_probs:
            self.logger.info("Run with %d fault_prob and %d timeout", fault_prob, timeout_suite)
            for kirk_suite, perf_suite in zip(
                self.kirk_suites,
                self.perf_suites,
                strict=True,
            ):
                started_at = datetime.now(UTC)
                kirk_future = executor.submit(
                    kirk.run,
                    scenarios=[kirk_suite],
                    timeout=timeout_suite,
                    fault_prob=fault_prob,
                    fault_interval=5,
                )
                sleep(1)

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

                result, metrics_path = kirk_future.result()
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


class FaultInjectionFioTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Fio test with fault injection.",
            frozenset({Subsystem.FILE}),
            timeout,
        )

    @property
    def kirk_suites(self) -> tuple[str, str]:
        return ("dio", "syscalls")

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
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        if not validate_fault_injection(client):
            self.logger.warning("Skipping test due to fault injection is supported on poky.")
            return TestResult(status=TestStatus.SKIPPED)

        kirk = Kirk(client)
        if not validate_kirk_suites(kirk, self.kirk_suites):
            self.logger.warning("Kirk suite not available for the image with LTP.")
            return TestResult(status=TestStatus.SKIPPED)

        timeout_suite = 1 + timeout // (len(self.kirk_suites) * len(self.fault_probs))

        for fault_prob in self.fault_probs:
            self.logger.info("Run with %d fault_prob and %d timeout", fault_prob, timeout_suite)
            for kirk_suite, fio_suite in zip(
                self.kirk_suites,
                self.fio_suites,
                strict=True,
            ):
                started_at = datetime.now(UTC)
                kirk_future = executor.submit(
                    kirk.run,
                    scenarios=[kirk_suite],
                    timeout=timeout_suite,
                    fault_prob=fault_prob,
                    fault_interval=5,
                )
                sleep(1)

                fio_config = FioSuiteConfig(
                    suite="fault_injection",
                    duration_sec=timeout_suite,
                    results_dir=Path().home() / "fio",
                    workloads=(fio_suite,),
                )

                fio = FioSuite(client, fio_config).run()
                yield from fio

                result, metrics_path = kirk_future.result()
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


def validate_fault_injection(client: SSHClient) -> bool:
    os_id = get_os_release(client).id
    if os_id and os_id != Distro.POKY.value:
        return False
    return not (os_id and os_id != Distro.POKY.value)


def validate_kirk_suites(kirk: Kirk, required_suites: tuple[str, ...]) -> bool:
    available_suites = kirk.list_suites()
    return all(suite in available_suites for suite in required_suites)
