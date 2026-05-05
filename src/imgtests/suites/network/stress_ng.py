from __future__ import annotations

from concurrent.futures import TimeoutError as FuturesTimeoutError
from datetime import datetime
from time import monotonic
from typing import TYPE_CHECKING, Final, NamedTuple

from imgtests.exec.loaders import StressNg
from imgtests.suites.general.stress_ng import StressNgTest
from imgtests.suites.network.common import (
    IPERF3_SERVER_SHUTDOWN_TIMEOUT_SEC,
    IPERF3_SERVER_STARTUP_SEC,
    Iperf3Tools,
    iperf3_metrics,
    iperf3_tools,
    join_commands,
    missing_ssh_client_result,
    server_wait_timeout,
    start_iperf3_server,
    utc_now,
    wait_iperf3_server,
)
from imgtests.types import Subsystem, TestResult, TestStatus

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import Future, ThreadPoolExecutor

    from imgtests.exec.exec import ExecResult, SSHClient
    from imgtests.exec.loaders.stress_ng import StressNGResult

__all__ = ("StressNgEnduranceNetworkTest", "StressNgMaxNetworkLoadTest")

STRESS_NG_RANDOM_SEED: Final = 0x5EED_1234
NETWORK_STRESS_MIN_RUN_SEC: Final = 1


class StressNgNetworkContext(NamedTuple):
    executor: ThreadPoolExecutor
    ssh_client: SSHClient
    stress_ng: StressNg
    iperf3: Iperf3Tools
    run_timeout: int
    deadline: float


class StressNgNetworkRun(NamedTuple):
    started_at: datetime
    stress_ng_result: ExecResult
    stress_ng_metrics: StressNGResult
    iperf3_client_result: ExecResult
    iperf3_server_result: ExecResult


def _network_load_run_timeout(timeout: int) -> int:
    reserved_overhead_sec = IPERF3_SERVER_STARTUP_SEC + IPERF3_SERVER_SHUTDOWN_TIMEOUT_SEC
    return timeout - reserved_overhead_sec


def _network_load_returncode_metrics(run: StressNgNetworkRun) -> dict[str, int]:
    return {
        "stress_ng_returncode": run.stress_ng_result.returncode,
        "iperf3_client_returncode": run.iperf3_client_result.returncode,
        "iperf3_server_returncode": run.iperf3_server_result.returncode,
    }


class StressNgEnduranceNetworkTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Stress-ng endurance network test.",
            frozenset({Subsystem.NETWORK}),
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
            sock=0,
            sock_ops=1000,
            netdev=0,
            udp=0,
        )


class StressNgMaxNetworkLoadTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Stress-ng maximum network load test.",
            frozenset({Subsystem.NETWORK}),
            timeout,
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        if client is None:
            yield missing_ssh_client_result()
            return

        run_timeout = _network_load_run_timeout(timeout)
        if run_timeout < NETWORK_STRESS_MIN_RUN_SEC:
            yield self._not_enough_run_time_result(timeout)
            return

        context = StressNgNetworkContext(
            executor=executor,
            ssh_client=client,
            stress_ng=StressNg(client),
            iperf3=iperf3_tools(client),
            run_timeout=run_timeout,
            deadline=monotonic() + timeout,
        )
        yield self._run_network_load(context)

    def _not_enough_run_time_result(self, timeout: int) -> TestResult:
        required_timeout_sec = (
            IPERF3_SERVER_STARTUP_SEC
            + IPERF3_SERVER_SHUTDOWN_TIMEOUT_SEC
            + NETWORK_STRESS_MIN_RUN_SEC
        )
        return TestResult(
            status=TestStatus.BROKEN,
            metrics={
                "provided_timeout_sec": timeout,
                "required_timeout_sec": required_timeout_sec,
            },
        )

    def _run_network_load(self, context: StressNgNetworkContext) -> TestResult:
        started_at = utc_now()
        server_future = start_iperf3_server(context.executor, context.iperf3.server)
        stress_ng_future = self._start_network_stress(context)
        iperf3_result = context.iperf3.client.run(
            client=context.ssh_client.hostname,
            time=context.run_timeout,
            interval=1,
            version4=True,
        )
        if iperf3_result.returncode:
            context.iperf3.server.stop_server()

        try:
            stress_ng_result, stress_ng_metrics = self._wait_network_stress(
                context,
                stress_ng_future,
            )
        except FuturesTimeoutError:
            self.logger.exception("Stress-ng maximum network load test FAILED: stress-ng timed out")
            return self._stress_ng_timeout_result(started_at, iperf3_result)

        try:
            server_result = wait_iperf3_server(
                context.iperf3.server,
                server_future,
                server_wait_timeout(context.deadline, IPERF3_SERVER_SHUTDOWN_TIMEOUT_SEC),
            )
        except FuturesTimeoutError:
            self.logger.exception(
                "Stress-ng maximum network load test FAILED: iperf3 server timed out",
            )
            return self._iperf3_server_timeout_result(
                started_at,
                stress_ng_result,
                iperf3_result,
            )

        return self._network_load_result(
            context,
            StressNgNetworkRun(
                started_at=started_at,
                stress_ng_result=stress_ng_result,
                stress_ng_metrics=stress_ng_metrics,
                iperf3_client_result=iperf3_result,
                iperf3_server_result=server_result,
            ),
        )

    def _start_network_stress(
        self,
        context: StressNgNetworkContext,
    ) -> Future[tuple[ExecResult, StressNGResult]]:
        return context.executor.submit(
            context.stress_ng.run,
            timeout_sec=context.run_timeout,
            sock=0,
            netdev=0,
            udp_flood=0,
            maximize=True,
            seed=STRESS_NG_RANDOM_SEED,
        )

    def _wait_network_stress(
        self,
        context: StressNgNetworkContext,
        stress_ng_future: Future[tuple[ExecResult, StressNGResult]],
    ) -> tuple[ExecResult, StressNGResult]:
        try:
            return stress_ng_future.result(timeout=max(0.0, context.deadline - monotonic()))
        except FuturesTimeoutError:
            context.iperf3.server.stop_server()
            raise

    def _stress_ng_timeout_result(
        self,
        started_at: datetime,
        iperf3_result: ExecResult,
    ) -> TestResult:
        return TestResult(
            status=TestStatus.FAILED,
            started_at=started_at,
            command=" ".join(iperf3_result.cmd),
            metrics={
                "iperf3_client_returncode": iperf3_result.returncode,
                "error": "stress-ng timed out",
            },
        )

    def _iperf3_server_timeout_result(
        self,
        started_at: datetime,
        stress_ng_result: ExecResult,
        iperf3_result: ExecResult,
    ) -> TestResult:
        return TestResult(
            status=TestStatus.FAILED,
            started_at=started_at,
            command=join_commands(stress_ng_result, iperf3_result),
            metrics={
                "stress_ng_returncode": stress_ng_result.returncode,
                "iperf3_client_returncode": iperf3_result.returncode,
                "error": "iperf3 server timed out",
            },
        )

    def _network_load_result(
        self,
        context: StressNgNetworkContext,
        run: StressNgNetworkRun,
    ) -> TestResult:
        command = join_commands(run.stress_ng_result, run.iperf3_client_result)

        if run.stress_ng_result.returncode == context.stress_ng.INCORRECT_OPT_OR_FATAL_ISSUE_CODE:
            self.logger.error("Stress-ng maximum network load test BROKEN")
            return self._network_load_failed_result(TestStatus.BROKEN, command, run)

        if (
            run.stress_ng_result.returncode
            or run.iperf3_client_result.returncode
            or run.iperf3_server_result.returncode
        ):
            self.logger.error("Stress-ng maximum network load test FAILED")
            return self._network_load_failed_result(TestStatus.FAILED, command, run)

        return TestResult(
            status=TestStatus.PASSED,
            started_at=run.started_at,
            command=command,
            metrics={
                **context.stress_ng.metrics_to_json(run.stress_ng_metrics),
                "iperf3": iperf3_metrics(
                    context.iperf3,
                    run.iperf3_client_result,
                    run.iperf3_server_result,
                ),
            },
        )

    def _network_load_failed_result(
        self,
        status: TestStatus,
        command: str,
        run: StressNgNetworkRun,
    ) -> TestResult:
        return TestResult(
            status=status,
            started_at=run.started_at,
            command=command,
            metrics=_network_load_returncode_metrics(run),
        )
