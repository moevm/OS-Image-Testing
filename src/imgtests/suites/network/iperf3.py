from __future__ import annotations

from concurrent.futures import TimeoutError as FuturesTimeoutError
from time import monotonic
from typing import TYPE_CHECKING, Any, Final, NamedTuple

from imgtests.exec.loaders import Iperf3
from imgtests.planning import AbstractRunnableTimeLimitedTest
from imgtests.suites.network.common import (
    IPERF3_LOCAL_SERVER_SHUTDOWN_TIMEOUT_SEC,
    IPERF3_SERVER_SHUTDOWN_TIMEOUT_SEC,
    IPERF3_SERVER_STARTUP_SEC,
    Iperf3Tools,
    iperf3_metrics,
    iperf3_tools,
    missing_ssh_client_result,
    server_wait_timeout,
    start_iperf3_server,
    utc_now,
    wait_iperf3_server,
)
from imgtests.types import Subsystem, TestResult, TestStatus

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient

__all__ = (
    "Iperf3LocalTest",
    "Iperf3PacketRateScalingTest",
    "Iperf3PpsProfile",
    "build_iperf3_pps_profiles",
    "get_subtest_timeout",
)

# PPS means packets per second.
IPERF3_START_PPS: Final = 2_000
IPERF3_STOP_PPS: Final = 8_000
IPERF3_STEP_PPS: Final = 2_000
IPERF3_DATAGRAM_SIZES_BYTES: Final = (64, 512, 1400)
IPERF3_LOCAL_MODES_UDP: Final = (False, True)
# Reserve a small gap per subtest for server startup, teardown, and scheduling jitter.
IPERF3_SUBTEST_OVERHEAD_SEC: Final = 1
# Do not schedule subtests shorter than this to avoid meaningless or flaky measurements.
IPERF3_MIN_SUBTEST_DURATION_SEC: Final = 1


class Iperf3PpsProfile(NamedTuple):
    pps: int
    datagram_size_bytes: int
    bitrate_bps: int


class Iperf3LocalContext(NamedTuple):
    executor: ThreadPoolExecutor
    ssh_client: SSHClient
    tools: Iperf3Tools
    timeout: int


class Iperf3ProfileTiming(NamedTuple):
    profiles_left: int
    remaining_timeout_sec: int
    duration_sec: int


class Iperf3ProfileOutcome(NamedTuple):
    result: TestResult
    stop_suite: bool = False


class PacketRateContext(NamedTuple):
    executor: ThreadPoolExecutor
    ssh_client: SSHClient
    tools: Iperf3Tools
    deadline: float


def build_iperf3_pps_profiles() -> tuple[Iperf3PpsProfile, ...]:
    return tuple(
        Iperf3PpsProfile(
            pps=pps,
            datagram_size_bytes=datagram_size_bytes,
            bitrate_bps=pps * datagram_size_bytes * 8,
        )
        for pps in range(
            IPERF3_START_PPS,
            IPERF3_STOP_PPS + IPERF3_STEP_PPS,
            IPERF3_STEP_PPS,
        )
        for datagram_size_bytes in IPERF3_DATAGRAM_SIZES_BYTES
    )


def get_subtest_timeout(timeout: int, subtests_count: int, reserved_overhead_sec: int) -> int:
    available_timeout = timeout - (subtests_count * reserved_overhead_sec)
    if available_timeout < subtests_count:
        return 0
    return available_timeout // subtests_count


def _packet_rate_metrics(
    profile: Iperf3PpsProfile,
    duration_sec: int | None = None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "pps": profile.pps,
        "datagram_size_bytes": profile.datagram_size_bytes,
        "bitrate_bps": profile.bitrate_bps,
    }
    if duration_sec is not None:
        metrics["duration_sec"] = duration_sec
    return metrics


def _packet_rate_reserved_overhead_sec() -> int:
    return IPERF3_SERVER_STARTUP_SEC + IPERF3_SUBTEST_OVERHEAD_SEC


def _packet_rate_profile_timing(
    deadline: float,
    profile_index: int,
    profiles_count: int,
    reserved_overhead_sec: int,
) -> Iperf3ProfileTiming:
    profiles_left = profiles_count - profile_index
    remaining_timeout_sec = max(0, int(deadline - monotonic()))
    return Iperf3ProfileTiming(
        profiles_left=profiles_left,
        remaining_timeout_sec=remaining_timeout_sec,
        duration_sec=get_subtest_timeout(
            remaining_timeout_sec,
            profiles_left,
            reserved_overhead_sec,
        ),
    )


class Iperf3LocalTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Test network with server on the tested node and client on the test runner.",
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

        context = Iperf3LocalContext(
            executor=executor,
            ssh_client=client,
            tools=iperf3_tools(client),
            timeout=timeout,
        )
        for udp in IPERF3_LOCAL_MODES_UDP:
            yield self._run_iperf3_mode(context, udp)

    def _run_iperf3_mode(self, context: Iperf3LocalContext, udp: bool) -> TestResult:
        started_at = utc_now()
        server_future = start_iperf3_server(context.executor, context.tools.server)

        client_result = context.tools.client.run(
            client=context.ssh_client.hostname,
            time=context.timeout,
            udp=udp,
            version4=True,
        )
        if client_result.returncode:
            self.logger.error("Error occurred while launching iperf3 client.")
            context.tools.server.stop_server()
            return TestResult(
                command=" ".join(client_result.cmd),
                metrics={"client_returncode": client_result.returncode},
                started_at=started_at,
                status=TestStatus.FAILED,
            )

        try:
            server_result = wait_iperf3_server(
                context.tools.server,
                server_future,
                IPERF3_LOCAL_SERVER_SHUTDOWN_TIMEOUT_SEC,
            )
        except FuturesTimeoutError:
            self.logger.exception("Error occurred while waiting for iperf3 server.")
            return TestResult(
                command=" ".join(client_result.cmd),
                metrics={"error": "iperf3 server timed out"},
                started_at=started_at,
                status=TestStatus.FAILED,
            )

        return TestResult(
            command=" ".join(client_result.cmd),
            metrics=Iperf3.split_result(
                raw_metrics=iperf3_metrics(context.tools, client_result, server_result),
            ),
            started_at=started_at,
            status=TestStatus.PASSED,
        )


class Iperf3PacketRateScalingTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Iperf3 UDP packet-rate scaling network test.",
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

        profiles = build_iperf3_pps_profiles()
        reserved_overhead_sec = _packet_rate_reserved_overhead_sec()
        timeout_error = self._not_enough_timeout_result(
            timeout,
            len(profiles),
            reserved_overhead_sec,
        )
        if timeout_error is not None:
            yield timeout_error
            return

        context = PacketRateContext(
            executor=executor,
            ssh_client=client,
            tools=iperf3_tools(client),
            deadline=monotonic() + timeout,
        )
        yield from self._run_profiles(context, profiles, timeout, reserved_overhead_sec)

    def _not_enough_timeout_result(
        self,
        timeout: int,
        profiles_count: int,
        reserved_overhead_sec: int,
    ) -> TestResult | None:
        subtest_timeout = get_subtest_timeout(timeout, profiles_count, reserved_overhead_sec)
        if subtest_timeout >= IPERF3_MIN_SUBTEST_DURATION_SEC:
            return None

        self.logger.error("Iperf3 UDP packet-rate scaling test BROKEN: not enough timeout")
        return TestResult(
            status=TestStatus.BROKEN,
            metrics={
                "profiles_count": profiles_count,
                "required_timeout_sec": profiles_count
                * (reserved_overhead_sec + IPERF3_MIN_SUBTEST_DURATION_SEC),
                "provided_timeout_sec": timeout,
            },
        )

    def _run_profiles(
        self,
        context: PacketRateContext,
        profiles: tuple[Iperf3PpsProfile, ...],
        timeout: int,
        reserved_overhead_sec: int,
    ) -> Iterable[TestResult]:
        for index, profile in enumerate(profiles):
            timing = _packet_rate_profile_timing(
                context.deadline,
                index,
                len(profiles),
                reserved_overhead_sec,
            )

            if timing.duration_sec < IPERF3_MIN_SUBTEST_DURATION_SEC:
                yield self._timeout_exhausted_result(len(profiles), index, timeout, timing)
                return

            outcome = self._run_profile(context, profile, timing)
            yield outcome.result
            if outcome.stop_suite:
                return

    def _timeout_exhausted_result(
        self,
        profiles_count: int,
        profiles_completed: int,
        timeout: int,
        timing: Iperf3ProfileTiming,
    ) -> TestResult:
        self.logger.error("Iperf3 UDP packet-rate scaling test BROKEN: timeout exhausted")
        return TestResult(
            status=TestStatus.BROKEN,
            metrics={
                "profiles_total": profiles_count,
                "profiles_completed": profiles_completed,
                "profiles_left": timing.profiles_left,
                "provided_timeout_sec": timeout,
                "remaining_timeout_sec": timing.remaining_timeout_sec,
            },
        )

    def _run_profile(
        self,
        context: PacketRateContext,
        profile: Iperf3PpsProfile,
        timing: Iperf3ProfileTiming,
    ) -> Iperf3ProfileOutcome:
        started_at = utc_now()
        server_future = start_iperf3_server(context.executor, context.tools.server)

        client_result = context.tools.client.run(
            client=context.ssh_client.hostname,
            time=timing.duration_sec,
            interval=1,
            udp=True,
            version4=True,
            bitrate=profile.bitrate_bps,
            length=profile.datagram_size_bytes,
        )
        if client_result.returncode:
            context.tools.server.stop_server()

        try:
            server_result = wait_iperf3_server(
                context.tools.server,
                server_future,
                server_wait_timeout(context.deadline, IPERF3_SERVER_SHUTDOWN_TIMEOUT_SEC),
            )
        except FuturesTimeoutError:
            self.logger.exception(
                "Iperf3 UDP packet-rate scaling test FAILED: server timed out",
            )
            metrics = _packet_rate_metrics(profile, timing.duration_sec)
            metrics.update(
                {
                    "client_returncode": client_result.returncode,
                    "error": "iperf3 server timed out",
                },
            )
            return Iperf3ProfileOutcome(
                result=TestResult(
                    status=TestStatus.FAILED,
                    started_at=started_at,
                    command=" ".join(client_result.cmd),
                    metrics=metrics,
                ),
                stop_suite=True,
            )

        if client_result.returncode or server_result.returncode:
            self.logger.error("Iperf3 UDP packet-rate scaling test FAILED")
            metrics = _packet_rate_metrics(profile)
            metrics.update(
                {
                    "client_returncode": client_result.returncode,
                    "server_returncode": server_result.returncode,
                },
            )
            return Iperf3ProfileOutcome(
                result=TestResult(
                    status=TestStatus.FAILED,
                    started_at=started_at,
                    command=" ".join(client_result.cmd),
                    metrics=metrics,
                ),
            )

        metrics = _packet_rate_metrics(profile, timing.duration_sec)
        metrics.update(iperf3_metrics(context.tools, client_result, server_result))
        return Iperf3ProfileOutcome(
            result=TestResult(
                command=" ".join(client_result.cmd),
                metrics=metrics,
                started_at=started_at,
                status=TestStatus.PASSED,
            ),
        )
