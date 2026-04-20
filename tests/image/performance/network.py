from concurrent.futures import TimeoutError as FuturesTimeoutError
from datetime import datetime
from time import sleep
from typing import TYPE_CHECKING, Final
from zoneinfo import ZoneInfo

from imgtests.exec.loaders import Iperf3
from imgtests.runner import AbstractRunnableTimeLimitedTest, TestResult, TestStatus
from imgtests.types import Subsystem

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


IPERF3_SERVER_STARTUP_SEC: Final = 1
IPERF3_SERVER_SHUTDOWN_TIMEOUT_SEC: Final = 5


class Iperf3LocalTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Load local network with iperf3.",
            frozenset({Subsystem.NETWORK}),
            timeout,
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        """Test network with server on the tested node and client on the test runner."""
        if client is None:
            yield TestResult(
                status=TestStatus.BROKEN,
                metrics={"error": "SSH client is not provided"},
            )
            return

        server_iperf3 = Iperf3(client)
        client_iperf3 = Iperf3()

        for udp in (False, True):
            started_at = datetime.now(tz=ZoneInfo("UTC"))
            server_future = executor.submit(
                server_iperf3.run,
                server=True,
                one_off=True,
                version4=True,
            )
            sleep(IPERF3_SERVER_STARTUP_SEC)

            ret = client_iperf3.run(
                client=client.hostname,
                time=timeout,
                udp=udp,
                version4=True,
            )
            if ret.returncode:
                self.logger.error("Error occurred while launching iperf3 client.")
                server_iperf3.stop_server()
                yield TestResult(
                    command=" ".join(ret.cmd),
                    metrics={"client_returncode": ret.returncode},
                    started_at=started_at,
                    status=TestStatus.FAILED,
                )
                return

            try:
                server_result = server_future.result(timeout=IPERF3_SERVER_SHUTDOWN_TIMEOUT_SEC)
            except FuturesTimeoutError:
                server_iperf3.stop_server()
                self.logger.exception("Error occurred while waiting for iperf3 server.")
                yield TestResult(
                    command=" ".join(ret.cmd),
                    metrics={"error": "iperf3 server timed out"},
                    started_at=started_at,
                    status=TestStatus.FAILED,
                )
                return

            yield TestResult(
                command=" ".join(ret.cmd),
                metrics={
                    "client": client_iperf3.metrics_to_json(ret.stdout.strip()),
                    "server": server_iperf3.metrics_to_json(server_result.stdout.strip()),
                },
                started_at=started_at,
                status=TestStatus.PASSED,
            )
