import logging

from imgtests.exec.exec import SSHClient
from imgtests.exec.loaders import StressNg

logger = logging.getLogger(__name__)


def test_endurance_disks_stress_ng(client: SSHClient | None) -> None:
    if client is None:
        logger.warning("SSH client is None, skipping")
        return

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
