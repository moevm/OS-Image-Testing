from typing import TYPE_CHECKING

from imgtests.exec.loaders import PhoronixTestSuite, setup_pts
from imgtests.runner import AbstractRunnableManyTimesTest

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


class PTSSystemTest(AbstractRunnableManyTimesTest):
    def __init__(self, iterations: int = 1) -> None:
        super().__init__("Load system with PTS.", {"system"}, iterations)

    def _run(self, executor: ThreadPoolExecutor, client: SSHClient | None, iterations: int) -> None:
        pts = PhoronixTestSuite(client)
        future = executor.submit(setup_pts, client)
        result = future.result()
        if result.returncode:
            self.logger.error("PTS setup failed: '%s'", result.stderr)
            return

        future = executor.submit(pts.run, test_name="pts/ctx-clock", run_count=iterations)
        result = future.result()
        self.logger.info(result)

        future = executor.submit(pts.run, test_name="pts/appleseed", run_count=iterations)
        result = future.result()
        self.logger.info(result)
