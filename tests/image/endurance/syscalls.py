import logging
from typing import TYPE_CHECKING

from imgtests.exec.loaders import Kirk, StressNg

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


logger = logging.getLogger(__name__)


def test_ltp_syscalls(_: ThreadPoolExecutor, client: SSHClient | None) -> None:
    kirk = Kirk(client)
    available_suites = kirk.list_suites()
    logger.info("Available LTP suites %s", available_suites)
    if "syscalls" not in available_suites:
        logger.warning("'syscalls' suite not available for the image with LTP.")
        return
    kirk.run(["syscalls"])


def test_syscalls_all_stress_ng(_: ThreadPoolExecutor, client: SSHClient) -> None:
    stress_ng = StressNg(client)
    result, (metrics, summary) = stress_ng.run(
        timeout_sec=60,
        syscall=0,
        syscall_method="all",
    )
    if result.returncode:
        logger.error("stress-ng syscalls failed")
    else:
        logger.info(summary)
        logger.info(metrics)
