from __future__ import annotations

from concurrent.futures import TimeoutError as FuturesTimeoutError
from datetime import datetime
from time import monotonic, sleep
from typing import TYPE_CHECKING, Final, NamedTuple
from zoneinfo import ZoneInfo

from imgtests.exec.loaders import Iperf3, StressNg
from imgtests.runner import AbstractRunnableTimeLimitedTest, TestResult, TestStatus
from imgtests.suites.general.stress_ng import StressNgTest
from imgtests.types import Subsystem

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient

# PPS means packets per second.
IPERF3_START_PPS: Final = 2_000
IPERF3_STOP_PPS: Final = 8_000
IPERF3_STEP_PPS: Final = 2_000
IPERF3_DATAGRAM_SIZES_BYTES: Final = (64, 512, 1400)
# Give the iperf3 server a small buffer to bind the socket and start accepting clients.
IPERF3_SERVER_STARTUP_SEC: Final = 1
# Reserve a small gap per subtest for server startup, teardown, and scheduling jitter.
IPERF3_SUBTEST_OVERHEAD_SEC: Final = 1
# Do not schedule subtests shorter than this to avoid meaningless or flaky measurements.
IPERF3_MIN_SUBTEST_DURATION_SEC: Final = 1
# Wait briefly for the one-off iperf3 server to exit after the client finishes.
IPERF3_SERVER_SHUTDOWN_TIMEOUT_SEC: Final = 2
STRESS_NG_RANDOM_SEED: Final = 0x5EED_1234


class Iperf3PpsProfile(NamedTuple):
    pps: int
    datagram_size_bytes: int
    bitrate_bps: int


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


class Iperf3PacketRateScalingTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Iperf3 UDP packet-rate scaling network test.",
            frozenset({Subsystem.NETWORK}),
            timeout,
        )

    def _run(
        self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int
    ) -> Iterable[TestResult]:
        if client is None:
            yield TestResult(
                status=TestStatus.BROKEN,
                metrics={"error": "SSH client is not provided"},
            )
            return

        server_iperf3 = Iperf3(client)
        client_iperf3 = Iperf3()
        profiles = build_iperf3_pps_profiles()

        reserved_overhead_sec = IPERF3_SERVER_STARTUP_SEC + IPERF3_SUBTEST_OVERHEAD_SEC
        subtest_timeout = get_subtest_timeout(
            timeout,
            len(profiles),
            reserved_overhead_sec,
        )
        deadline = monotonic() + timeout

        if subtest_timeout < IPERF3_MIN_SUBTEST_DURATION_SEC:
            self.logger.error("Iperf3 UDP packet-rate scaling test BROKEN: not enough timeout")
            yield TestResult(
                status=TestStatus.BROKEN,
                metrics={
                    "profiles_count": len(profiles),
                    "required_timeout_sec": len(profiles)
                    * (reserved_overhead_sec + IPERF3_MIN_SUBTEST_DURATION_SEC),
                    "provided_timeout_sec": timeout,
                },
            )
            return

        for index, profile in enumerate(profiles):
            profiles_left = len(profiles) - index
            remaining_timeout = max(0, int(deadline - monotonic()))
            current_subtest_timeout = get_subtest_timeout(
                remaining_timeout,
                profiles_left,
                reserved_overhead_sec,
            )

            if current_subtest_timeout < IPERF3_MIN_SUBTEST_DURATION_SEC:
                self.logger.error("Iperf3 UDP packet-rate scaling test BROKEN: timeout exhausted")
                yield TestResult(
                    status=TestStatus.BROKEN,
                    metrics={
                        "profiles_total": len(profiles),
                        "profiles_completed": index,
                        "profiles_left": profiles_left,
                        "provided_timeout_sec": timeout,
                        "remaining_timeout_sec": remaining_timeout,
                    },
                )
                return

            started_at = datetime.now(tz=ZoneInfo("UTC"))
            server_future = executor.submit(
                server_iperf3.run,
                server=True,
                one_off=True,
                version4=True,
            )
            sleep(IPERF3_SERVER_STARTUP_SEC)

            result = client_iperf3.run(
                client=client.hostname,
                time=current_subtest_timeout,
                interval=1,
                udp=True,
                version4=True,
                bitrate=profile.bitrate_bps,
                length=profile.datagram_size_bytes,
            )

            if result.returncode:
                server_iperf3.stop_server()

            try:
                server_wait_timeout = max(
                    0,
                    min(
                        IPERF3_SERVER_SHUTDOWN_TIMEOUT_SEC,
                        deadline - monotonic(),
                    ),
                )
                server_result = server_future.result(timeout=server_wait_timeout)
            except FuturesTimeoutError:
                server_iperf3.stop_server()
                self.logger.exception(
                    "Iperf3 UDP packet-rate scaling test FAILED: server timed out"
                )
                yield TestResult(
                    status=TestStatus.FAILED,
                    started_at=started_at,
                    command=" ".join(result.cmd),
                    metrics={
                        "pps": profile.pps,
                        "datagram_size_bytes": profile.datagram_size_bytes,
                        "bitrate_bps": profile.bitrate_bps,
                        "duration_sec": current_subtest_timeout,
                        "client_returncode": result.returncode,
                        "error": "iperf3 server timed out",
                    },
                )
                return

            if result.returncode or server_result.returncode:
                self.logger.error("Iperf3 UDP packet-rate scaling test FAILED")
                yield TestResult(
                    status=TestStatus.FAILED,
                    started_at=started_at,
                    command=" ".join(result.cmd),
                    metrics={
                        "pps": profile.pps,
                        "datagram_size_bytes": profile.datagram_size_bytes,
                        "bitrate_bps": profile.bitrate_bps,
                        "client_returncode": result.returncode,
                        "server_returncode": server_result.returncode,
                    },
                )
                continue

            yield TestResult(
                command=" ".join(result.cmd),
                metrics={
                    "pps": profile.pps,
                    "datagram_size_bytes": profile.datagram_size_bytes,
                    "bitrate_bps": profile.bitrate_bps,
                    "duration_sec": current_subtest_timeout,
                    "client": client_iperf3.metrics_to_json(result.stdout.strip()),
                    "server": server_iperf3.metrics_to_json(server_result.stdout.strip()),
                },
                started_at=started_at,
                status=TestStatus.PASSED,
            )


class StressNgMaxNetworkLoadTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Stress-ng maximum network load test.",
            frozenset({Subsystem.NETWORK}),
            timeout,
        )

    def _run(
        self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int
    ) -> Iterable[TestResult]:
        if client is None:
            yield TestResult(
                status=TestStatus.BROKEN,
                metrics={"error": "SSH client is not provided"},
            )
            return

        stress_ng = StressNg(client)
        server_iperf3 = Iperf3(client)
        client_iperf3 = Iperf3()

        reserved_overhead_sec = IPERF3_SERVER_STARTUP_SEC + IPERF3_SERVER_SHUTDOWN_TIMEOUT_SEC
        run_timeout = timeout - reserved_overhead_sec
        if run_timeout < 1:
            yield TestResult(
                status=TestStatus.BROKEN,
                metrics={
                    "provided_timeout_sec": timeout,
                    "required_timeout_sec": reserved_overhead_sec + 1,
                },
            )
            return

        deadline = monotonic() + timeout
        started_at = datetime.now(tz=ZoneInfo("UTC"))

        server_future = executor.submit(
            server_iperf3.run,
            server=True,
            one_off=True,
            version4=True,
        )
        sleep(IPERF3_SERVER_STARTUP_SEC)

        stress_ng_future = executor.submit(
            stress_ng.run,
            timeout_sec=run_timeout,
            sock=0,
            netdev=0,
            udp_flood=0,
            maximize=True,
            seed=STRESS_NG_RANDOM_SEED,
        )

        iperf3_result = client_iperf3.run(
            client=client.hostname,
            time=run_timeout,
            interval=1,
            version4=True,
        )

        if iperf3_result.returncode:
            server_iperf3.stop_server()

        try:
            stress_ng_result, stress_ng_metrics = stress_ng_future.result(
                timeout=max(0, deadline - monotonic())
            )
        except FuturesTimeoutError:
            server_iperf3.stop_server()
            self.logger.exception("Stress-ng maximum network load test FAILED: stress-ng timed out")
            yield TestResult(
                status=TestStatus.FAILED,
                started_at=started_at,
                command=" ".join(iperf3_result.cmd),
                metrics={
                    "iperf3_client_returncode": iperf3_result.returncode,
                    "error": "stress-ng timed out",
                },
            )
            return

        try:
            server_result = server_future.result(
                timeout=max(0, min(IPERF3_SERVER_SHUTDOWN_TIMEOUT_SEC, deadline - monotonic()))
            )
        except FuturesTimeoutError:
            server_iperf3.stop_server()
            self.logger.exception(
                "Stress-ng maximum network load test FAILED: iperf3 server timed out"
            )
            yield TestResult(
                status=TestStatus.FAILED,
                started_at=started_at,
                command=" ".join(stress_ng_result.cmd) + " & " + " ".join(iperf3_result.cmd),
                metrics={
                    "stress_ng_returncode": stress_ng_result.returncode,
                    "iperf3_client_returncode": iperf3_result.returncode,
                    "error": "iperf3 server timed out",
                },
            )
            return

        command = " ".join(stress_ng_result.cmd) + " & " + " ".join(iperf3_result.cmd)

        if stress_ng_result.returncode == stress_ng.INCORRECT_OPT_OR_FATAL_ISSUE_CODE:
            self.logger.error("Stress-ng maximum network load test BROKEN")
            yield TestResult(
                status=TestStatus.BROKEN,
                started_at=started_at,
                command=command,
                metrics={
                    "stress_ng_returncode": stress_ng_result.returncode,
                    "iperf3_client_returncode": iperf3_result.returncode,
                    "iperf3_server_returncode": server_result.returncode,
                },
            )
            return

        if stress_ng_result.returncode or iperf3_result.returncode or server_result.returncode:
            self.logger.error("Stress-ng maximum network load test FAILED")
            yield TestResult(
                status=TestStatus.FAILED,
                started_at=started_at,
                command=command,
                metrics={
                    "stress_ng_returncode": stress_ng_result.returncode,
                    "iperf3_client_returncode": iperf3_result.returncode,
                    "iperf3_server_returncode": server_result.returncode,
                },
            )
            return

        yield TestResult(
            status=TestStatus.PASSED,
            started_at=started_at,
            command=command,
            metrics={
                **stress_ng.metrics_to_json(stress_ng_metrics),
                "iperf3": {
                    "client": client_iperf3.metrics_to_json(iperf3_result.stdout.strip()),
                    "server": server_iperf3.metrics_to_json(server_result.stdout.strip()),
                },
            },
        )
