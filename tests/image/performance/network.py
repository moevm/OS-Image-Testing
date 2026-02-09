import logging
import os
from threading import Thread

import iperf3

from imgtests.exec.exec import SSHClient
from imgtests.exec.loaders import Iperf3

logger = logging.getLogger(__name__)


def run_server():
    server = iperf3.Server()
    server.one_off = True
    server.run()


def test_iperf3(client: SSHClient | None):
    iperf3_client = Iperf3(client)
    server_thread = Thread(target=run_server)
    server_thread.start()
    address = os.getenv("PYTHON_ADDRESS")
    ret = iperf3_client(["-c", address, "-t", "30", "-i", "5"])
    if ret.returncode:
        logger.error("Error occured while launching iperf3 server")
        return
    logger.info(ret.stdout)
