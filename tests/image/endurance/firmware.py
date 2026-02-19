import logging
from typing import TYPE_CHECKING

from imgtests.exec.loaders import Fwts

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


logger = logging.getLogger(__name__)


def test_fwts(executor: ThreadPoolExecutor, client: SSHClient | None) -> None:
    fwts = Fwts(client)
    future = executor.submit(fwts)
    r = future.result()
    if r.returncode:
        logger.error("FWTS endurance test FAILED")
    else:
        logger.info("FWTS endurance test PASSED")

    if r.stdout:
        logger.info("fwts stdout:\n%s", r.stdout)
    if r.stderr:
        logger.info("fwts stderr:\n%s", r.stderr)
