import logging
from typing import TYPE_CHECKING

from imgtests.exec.loaders import StressNg

if TYPE_CHECKING:
    from imgtests.exec.exec import SSHClient


logger = logging.getLogger(__name__)


def test_endurance_cpu_stress_ng(client: SSHClient | None) -> None:
    stress_ng = StressNg(client)
    result, (metrics, summary) = stress_ng.run(timeout_sec=10, cpu=0)

    if result.returncode:
        logger.error("CPU endurance test FAILED")
    else:
        logger.info("CPU endurance test PASSED")

    if summary:
        logger.info(summary)
    if metrics:
        logger.info(metrics)
