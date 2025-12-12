import logging
from concurrent.futures import ThreadPoolExecutor

from imgtests.exec.exec import SSHClient
from imgtests.exec.loaders.kirk import Kirk

logger = logging.getLogger(__name__)


def run_ltp_syscalls(executor: ThreadPoolExecutor, client: SSHClient | None = None) -> None:
    kirk = Kirk(client)
    future = executor.submit(kirk.list_suites)
    available_suites = future.result()
    logger.info("Available LTP suites %s", available_suites)
    if "syscalls" not in available_suites:
        logger.warning("'syscalls' suite not available for the image with LTP.")
        return
    kirk.run(["syscalls"])
