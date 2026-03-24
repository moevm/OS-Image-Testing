from typing import TYPE_CHECKING

from imgtests.exec.loaders import PhoronixTestSuite
from imgtests.runner import AbstractRunnableManyTimesTest, Subsystem, TestResult, TestStatus

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


class PTSSystemTest(AbstractRunnableManyTimesTest):
    def __init__(self, iterations: int = 1) -> None:
        super().__init__("Load system with PTS.", frozenset({Subsystem.SYSTEM}), iterations)

    def _run(
        self, executor: ThreadPoolExecutor, client: SSHClient | None, iterations: int
    ) -> TestResult:
        pts = PhoronixTestSuite(client)
        future = executor.submit(pts.prepare)
        result = future.result()
        if result.returncode:
            self.logger.error("PTS setup failed: '%s'", result.stderr)
            return TestResult(status=TestStatus.Broken)

        future = executor.submit(pts.run, test_name="pts/ctx-clock", run_count=iterations)
        _, result = future.result()
        self.logger.info(PhoronixTestSuite.parse_metrics(result))

        future = executor.submit(pts.run, test_name="pts/appleseed", run_count=iterations)
        _, result = future.result()
        self.logger.info(PhoronixTestSuite.parse_metrics(result))

        return TestResult(status=TestStatus.Passed)
