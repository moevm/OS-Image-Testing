import logging

from imgtests.exec.exec import SSHClient
from imgtests.exec.loaders import StressNg

logger = logging.getLogger(__name__)


def test_endurance_memory_stress_ng(client: SSHClient | None) -> None:
    stress_ng = StressNg(client)
    result, (metrics, summary) = stress_ng.run(
        timeout_sec=10,
        vm=2,
        vm_bytes="16M",
    )

    if result.returncode:
        logger.error("MEMORY endurance test FAILED")
    else:
        logger.info("MEMORY endurance test PASSED")

    if summary:
        logger.info(summary)
    if metrics:
        logger.info(metrics)
