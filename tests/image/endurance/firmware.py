import logging

from imgtests.exec.exec import SSHClient
from imgtests.exec.loaders import Fwts

logger = logging.getLogger(__name__)


def test_endurance_fwts(client: SSHClient | None) -> None:
    fwts = Fwts(client)
    r = fwts.run()
    if r.returncode:
        logger.error("FWTS endurance test FAILED")
    else:
        logger.info("FWTS endurance test PASSED")

    if r.stdout:
        logger.info("fwts stdout:\n%s", r.stdout)
    if r.stderr:
        logger.info("fwts stderr:\n%s", r.stderr)
