import logging

from imgtests.exec.exec import SSHClient
from imgtests.exec.loaders.kirk import Kirk
from imgtests.exec.loaders.stress_ng import StressNg

logger = logging.getLogger(__name__)


def test_ltp_syscalls(client: SSHClient | None) -> None:
    kirk = Kirk(client)
    available_suites = kirk.list_suites()
    logger.info("Available LTP suites %s", available_suites)
    if "syscalls" not in available_suites:
        logger.warning("'syscalls' suite not available for the image with LTP.")
        return
    kirk.run(["syscalls"])


def test_syscalls_all_stress_ng(client: SSHClient) -> None:
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
