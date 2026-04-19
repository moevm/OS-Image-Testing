from datetime import datetime
from time import sleep
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from imgtests.exec.loaders import Iperf3
from imgtests.runner import AbstractRunnableTimeLimitedTest, TestResult, TestStatus
from imgtests.types import Subsystem

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


class Iperf3LocalTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__("Load local network with iperf3.", frozenset({Subsystem.NETWORK}), timeout)

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        """Test remote network with server and client on the remote."""
        iperf3 = Iperf3(client)
        for udp in (False, True):
            started_at = datetime.now(tz=ZoneInfo("UTC"))
            server_future = executor.submit(iperf3.run, server=True, one_off=True, version4=True)
            sleep(1)
            ret = iperf3.run(
                client="localhost",
                time=timeout,
                udp=udp,
                version4=True,
            )
            if ret.returncode:
                self.logger.error("Error occurred while launching iperf3 client.")
                server_future.result(timeout=5)
                return TestResult(status=TestStatus.FAILED)
            server_result = server_future.result(timeout=5)
            yield TestResult(
                command=" ".join(ret.cmd),
                metrics={
                    "client": iperf3.metrics_to_json(ret.stdout.strip()),
                    "server": iperf3.metrics_to_json(server_result.stdout.strip()),
                },
                started_at=started_at,
                status=TestStatus.PASSED,
            )
