import logging
from typing import TYPE_CHECKING

from imgtests.exec.loaders import StressNg
from imgtests.exec.observers import Sar
from imgtests.runner import AbstractRunnableTimeLimitedTest, Subsystem

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient

logger = logging.getLogger(__name__)


class SarWithStressNGTest(AbstractRunnableTimeLimitedTest):
    """Tests that run stress-ng with sar to measure pgscan time."""

    def __init__(self, timeout: int) -> None:
        super().__init__("Stress-ng with sar measure pgscan time.", {Subsystem.MEMORY}, timeout)

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> None:
        sar = Sar(client)

        stress_ng = StressNg(client)
        stress_ng_future = executor.submit(
            stress_ng.run,
            timeout_sec=timeout,
            vm=4,
            vm_bytes="95%",
        )

        _, pgscan = sar.run(interval=1, count=timeout)
        _, m = stress_ng_future.result()

        logger.info("stress-ng metrics: %s", m)
        logger.info("pgscan time: %s s", pgscan)
