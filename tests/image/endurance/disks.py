import logging
from typing import TYPE_CHECKING

from imgtests.exec.loaders import StressNg

if TYPE_CHECKING:
    from imgtests.exec.exec import SSHClient

logger = logging.getLogger(__name__)


def test_endurance_disks_stress_ng(client: SSHClient | None) -> None:
    stress_ng = StressNg(client)
    result, (metrics, summary) = stress_ng.run(
        timeout_sec=10,
        hdd=1,
        hdd_bytes="100M",
        hdd_opts="sync",
    )

    if result.returncode:
        logger.error("DISK endurance test FAILED")
    else:
        logger.info("DISK endurance test PASSED")

    if summary is not None:
        logger.info(summary)
    if metrics:
        logger.info(metrics)
