from concurrent.futures import ThreadPoolExecutor
import logging
from typing import TYPE_CHECKING

from imgtests.runner import AbstractRunnableTimeLimitedTest
from imgtests.exec.observers.sar import Sar
from imgtests.exec.base_util import common_run_command

if TYPE_CHECKING:
    from imgtests.exec.exec import SSHClient

logger = logging.getLogger(__name__)

class SarWithStressNGTest(AbstractRunnableTimeLimitedTest):
    """Tests that run stress-ng with sar to measure pgscan time."""

    def __init__(self, timeout: int) -> None:
        super().__init__("Stress-ng with sar measure pgscan time.", {"memory"}, timeout)

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        timeout: int,
    ) -> None:
        sar = Sar(client)
        sar.prepare()

        common_run_command([f"stress-ng --vm 4 --vm-bytes 95% --timeout {timeout} &"], client)
        r, pgscan = sar.run(interval=1,count=timeout)
        logger.info(r)
        logger.info("pgscan = %s", pgscan)