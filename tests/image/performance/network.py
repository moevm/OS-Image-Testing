from time import sleep
from typing import TYPE_CHECKING

from imgtests.exec.loaders import Iperf3
from imgtests.runner import AbstractRunnableTimeLimitedTest, Subsystem

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


class Iperf3LocalTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__("Load local network with iperf3.", frozenset({Subsystem.NETWORK}), timeout)

    def _run(self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int) -> None:
        """Test remote network with server and client on the remote."""
        iperf3 = Iperf3(client)
        for udp in (False, True):
            server_future = executor.submit(iperf3.run, server=True, one_off=True, version4=True)
            sleep(1)
            # TODO: save result to the database
            ret = iperf3.run(
                client="localhost",
                time=timeout,
                udp=udp,
                version4=True,
            )
            if ret.returncode:
                self.logger.error("Error occurred while launching iperf3 client.")
                server_future.result(timeout=5)
                return
            server_future.result(timeout=5)
