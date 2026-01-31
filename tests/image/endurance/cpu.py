import logging

from imgtests.exec.exec import SSHClient
from imgtests.exec.loaders import StressNg

logger = logging.getLogger(__name__)


def test_endurance_cpu_stress_ng(client: SSHClient | None) -> None:
    if client is None:
        logger.warning("SSH client is None, skipping")
        return

    stress_ng = StressNg(client)
    result, (metrics, summary) = stress_ng.run(
        timeout_sec=10,
        cpu=0,
        verify=True,
    )

    if result.returncode:
        logger.error("CPU endurance test FAILED")
    else:
        logger.info("CPU endurance test PASSED")

    if summary:
        logger.info(summary)
    if metrics:
        logger.info(metrics)
