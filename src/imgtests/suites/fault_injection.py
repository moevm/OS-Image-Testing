import random
from datetime import datetime
from time import sleep
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from imgtests.exec.loaders import Chaosblade, Kirk
from imgtests.exec.osinfo import get_os_release
from imgtests.planning import AbstractRunnableTimeLimitedTest
from imgtests.types import Distro, Subsystem, TestResult, TestStatus

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


class FaultInjectionEnduranceTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int, iterations: int = 4) -> None:
        super().__init__(
            "Endurance test with periodic fault injection.",
            frozenset({Subsystem.FILE, Subsystem.SYSTEM}),
            timeout,
        )
        self.iterations = iterations

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        os_id = get_os_release(client).id
        if os_id and os_id != Distro.POKY.value:
            self.logger.warning("Skipping test due to fault injection is supported on poky.")
            return TestResult(status=TestStatus.SKIPPED)

        kirk = Kirk(client)
        available_suites = kirk.list_suites()
        scenarios = ["syscalls", "fs", "mm", "dio"]
        for suite in scenarios:
            if suite not in available_suites:
                self.logger.warning("'%s' suite not available for the image with LTP.", suite)
                return TestResult(status=TestStatus.SKIPPED)

        random.seed(timeout)
        fault_probabilities = [
            random.randint(30, 80) if i % 2 == 1 else 0  # noqa: S311
            for i in range(self.iterations)
        ]
        time_per_test = (timeout // self.iterations) + 1

        for fault_probability in fault_probabilities:
            started_at = datetime.now(tz=ZoneInfo("UTC"))
            result, metrics_path = kirk.run(
                scenarios=scenarios,
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

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        os_id = get_os_release(client).id
        if os_id and os_id != Distro.POKY.value:
            self.logger.warning("Skipping test due to fault injection is supported on poky.")
            return TestResult(status=TestStatus.SKIPPED)

        experiments = {
            "dio": {
                "method": "create_disk_exp",
                "params": {
                    "action": "fill",
                    "reserve_mb": 512,
                    "path": "/tmp/chaos-fault-injection",  # noqa: S108
                },
            },
            "sched": {
                "method": "create_cpu_exp",
                "params": {
                    "cpu_percent": 10,
                },
            },
        }
        fault_probs = [0, 50, 70, 90, 95]
        timeout_suite = max(timeout // (len(experiments.keys()) * len(fault_probs)), 10)

        chaosblade = Chaosblade(client)
        kirk = Kirk(client)
        available_suites = kirk.list_suites()
        for suite in experiments:
            if suite not in available_suites:
                self.logger.warning("'%s' suite not available for the image with LTP.", suite)
                return TestResult(status=TestStatus.SKIPPED)
        for fault_prob in fault_probs:
            self.logger.info("Run with %d fault_prob and %d timeout", fault_prob, timeout_suite)
            for kirk_suite, chaosblade_conf in experiments.items():
                started_at = datetime.now(tz=ZoneInfo("UTC"))
                kirk_future = executor.submit(
                    kirk.run,
                    scenarios=[kirk_suite],
                    timeout=timeout_suite,
                    fault_prob=fault_prob,
                    fault_interval=1,
                )
                sleep(1)
                chaosblade_future = executor.submit(
                    getattr(chaosblade, chaosblade_conf["method"]),
                    **chaosblade_conf["params"],
                    timeout_sec=timeout_suite,
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
