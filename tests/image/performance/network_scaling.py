from __future__ import annotations

from concurrent.futures import TimeoutError
from datetime import datetime
from time import monotonic, sleep
from typing import TYPE_CHECKING, Final, NamedTuple
from zoneinfo import ZoneInfo

from imgtests.exec.exec import common_run_command
from imgtests.exec.loaders import Iperf3, StressNg
from imgtests.runner import AbstractRunnableTimeLimitedTest, TestResult, TestStatus
from imgtests.suites.general.stress_ng import StressNgTest
from imgtests.types import Subsystem

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient

IPERF3_PACKET_RATE_START_PPS: Final = 2_000
IPERF3_PACKET_RATE_STOP_PPS: Final = 8_000
IPERF3_PACKET_RATE_STEP_PPS: Final = 2_000
IPERF3_DATAGRAM_SIZES_BYTES: Final = (64, 512, 1400)
IPERF3_SERVER_STARTUP_SEC: Final = 1
IPERF3_SUBTEST_OVERHEAD_SEC: Final = 1
IPERF3_MIN_SUBTEST_DURATION_SEC: Final = 1
IPERF3_SERVER_SHUTDOWN_TIMEOUT_SEC: Final = 2
STRESS_NG_RANDOM_SEED: Final = 0x5EED_1234


class Iperf3PacketRateProfile(NamedTuple):
    packet_rate_pps: int
    datagram_size_bytes: int
    bitrate_bps: int


def build_iperf3_packet_rate_profiles() -> tuple[Iperf3PacketRateProfile, ...]:
    return tuple(
        Iperf3PacketRateProfile(
            packet_rate_pps=packet_rate_pps,
            datagram_size_bytes=datagram_size_bytes,
            bitrate_bps=packet_rate_pps * datagram_size_bytes * 8,
        )
        for packet_rate_pps in range(
            IPERF3_PACKET_RATE_START_PPS,
            IPERF3_PACKET_RATE_STOP_PPS + IPERF3_PACKET_RATE_STEP_PPS,
            IPERF3_PACKET_RATE_STEP_PPS,
        )
        for datagram_size_bytes in IPERF3_DATAGRAM_SIZES_BYTES
    )


def get_subtest_timeout(timeout: int, subtests_count: int, reserved_overhead_sec: int) -> int:
    available_timeout = timeout - (subtests_count * reserved_overhead_sec)
    if available_timeout < subtests_count:
        return 0
    return available_timeout // subtests_count


def stop_iperf3_server(client: SSHClient | None) -> None:
    common_run_command(["pkill", "-f", "iperf3.*--server"], client)


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
        iperf3 = Iperf3(client)
        profiles = build_iperf3_packet_rate_profiles()
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
            server_future = executor.submit(iperf3.run, server=True, one_off=True, version4=True)
            sleep(IPERF3_SERVER_STARTUP_SEC)
            result = iperf3.run(
                client="localhost",
                time=current_subtest_timeout,
                interval=1,
                udp=True,
                version4=True,
                **{
                    "bitrate": profile.bitrate_bps,
                    "length": profile.datagram_size_bytes,
                },
            )

            if result.returncode:
                stop_iperf3_server(client)

            try:
                server_wait_timeout = max(
                    0,
                    min(
                        IPERF3_SERVER_SHUTDOWN_TIMEOUT_SEC,
                        deadline - monotonic(),
                    ),
                )
                server_result = server_future.result(timeout=server_wait_timeout)
            except TimeoutError:
                stop_iperf3_server(client)
                self.logger.error("Iperf3 UDP packet-rate scaling test FAILED: server timed out")
                yield TestResult(
                    status=TestStatus.FAILED,
                    started_at=started_at,
                    command=" ".join(result.cmd),
                    metrics={
                        "packet_rate_pps": profile.packet_rate_pps,
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
                        "packet_rate_pps": profile.packet_rate_pps,
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
                    "packet_rate_pps": profile.packet_rate_pps,
                    "datagram_size_bytes": profile.datagram_size_bytes,
                    "bitrate_bps": profile.bitrate_bps,
                    "duration_sec": current_subtest_timeout,
                    "client": iperf3.metrics_to_json(result.stdout.strip()),
                    "server": iperf3.metrics_to_json(server_result.stdout.strip()),
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
        stress_ng = StressNg(client)
        yield from self.run_test(
            stress_ng=stress_ng,
            executor=executor,
            timeout=timeout,
            sock=0,
            netdev=0,
            udp_flood=0,
            maximize=True,
            seed=STRESS_NG_RANDOM_SEED,
        )
