import logging
from concurrent.futures import ThreadPoolExecutor

from imgtests.exec.exec import SSHClient
from imgtests.exec.loaders import Iperf3

logger = logging.getLogger(__name__)


def test_iperf3(executor: ThreadPoolExecutor, client: SSHClient | None) -> None:
    """Test remote network with server and client on the remote."""
    iperf3 = Iperf3(client)
    for udp in (False, True):
        server_future = executor.submit(iperf3.run, server=True, one_off=True, version4=True)
        # TODO: save result to the database  # noqa: FIX002, TD002, TD003
        ret = iperf3.run(
            client="localhost",
            time=30,
            udp=udp,
            version4=True,
        )
        if ret.returncode:
            logger.error("Error occurred while launching iperf3 client.")
            server_future.result(timeout=5)
            return
        server_future.result(timeout=5)
