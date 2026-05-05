from __future__ import annotations

from concurrent.futures import TimeoutError as FuturesTimeoutError
from datetime import datetime
from time import monotonic, sleep
from typing import TYPE_CHECKING, Any, Final, NamedTuple
from zoneinfo import ZoneInfo

from imgtests.exec.loaders import Iperf3
from imgtests.types import TestResult, TestStatus

if TYPE_CHECKING:
    from concurrent.futures import Future, ThreadPoolExecutor

    from imgtests.exec.exec import ExecResult, SSHClient

# Give the iperf3 server a small buffer to bind the socket and start accepting clients.
IPERF3_SERVER_STARTUP_SEC: Final = 1
# Wait briefly for the one-off iperf3 server to exit after the client finishes.
IPERF3_SERVER_SHUTDOWN_TIMEOUT_SEC: Final = 2
IPERF3_LOCAL_SERVER_SHUTDOWN_TIMEOUT_SEC: Final = 5


class Iperf3Tools(NamedTuple):
    server: Iperf3
    client: Iperf3


def utc_now() -> datetime:
    return datetime.now(tz=ZoneInfo("UTC"))


def missing_ssh_client_result() -> TestResult:
    return TestResult(
        status=TestStatus.BROKEN,
        metrics={"error": "SSH client is not provided"},
    )


def iperf3_tools(client: SSHClient) -> Iperf3Tools:
    return Iperf3Tools(server=Iperf3(client), client=Iperf3())


def start_iperf3_server(
    executor: ThreadPoolExecutor,
    server_iperf3: Iperf3,
) -> Future[ExecResult]:
    server_future = executor.submit(
        server_iperf3.run,
        server=True,
        one_off=True,
        version4=True,
    )
    sleep(IPERF3_SERVER_STARTUP_SEC)
    return server_future


def wait_iperf3_server(
    server_iperf3: Iperf3,
    server_future: Future[ExecResult],
    timeout: float,
) -> ExecResult:
    try:
        return server_future.result(timeout=max(0.0, timeout))
    except FuturesTimeoutError:
        server_iperf3.stop_server()
        raise


def server_wait_timeout(deadline: float, max_timeout_sec: int) -> float:
    return max(0.0, min(float(max_timeout_sec), deadline - monotonic()))


def join_commands(*results: ExecResult) -> str:
    return " & ".join(" ".join(result.cmd) for result in results)


def iperf3_metrics(
    tools: Iperf3Tools,
    client_result: ExecResult,
    server_result: ExecResult,
) -> dict[str, Any]:
    return {
        "client": tools.client.metrics_to_json(client_result.stdout.strip()),
        "server": tools.server.metrics_to_json(server_result.stdout.strip()),
    }
