from typing import TYPE_CHECKING

from imgtests.exec.loaders import Fwts
from imgtests.planning import AbstractRunnableManyTimesTest
from imgtests.types import TestResult, TestStatus

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient
    from imgtests.types import Subsystem


class FwtsTest(AbstractRunnableManyTimesTest):
    def __init__(
        self,
        subsystems: frozenset[Subsystem],
        iterations: int = 1,
    ) -> None:
        super().__init__("FWTS firmware tests.", subsystems, iterations)

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        iterations: int,
    ) -> Iterable[TestResult]:
        fwts = Fwts(client)

        for _ in range(iterations):
            future = executor.submit(fwts.run)
            result, parsed = future.result()

            if result.returncode and not parsed.tests:
                self.logger.error("FWTS test BROKEN (returncode=%d)", result.returncode)
                yield TestResult(status=TestStatus.BROKEN)
                continue

            tests_passed = parsed.summary.get("passed", 0)
            tests_failed = parsed.summary.get("failed", 0)
            tests_skipped = parsed.summary.get("skipped", 0)
            tests_aborted = parsed.summary.get("aborted", 0)

            if tests_failed > 0:
                self.logger.error(
                    "FWTS test FAILED (%d passed, %d failed, %d skipped, %d aborted)",
                    tests_passed,
                    tests_failed,
                    tests_skipped,
                    tests_aborted,
                )
                yield TestResult(
                    status=TestStatus.FAILED,
                    metrics=fwts.metrics_to_json(parsed),
                    command="fwts",
                )
            else:
                self.logger.info(
                    "FWTS test PASSED (%d passed, %d failed, %d skipped, %d aborted)",
                    tests_passed,
                    tests_failed,
                    tests_skipped,
                    tests_aborted,
                )
                yield TestResult(
                    status=TestStatus.PASSED,
                    metrics=fwts.metrics_to_json(parsed),
                    command="fwts",
                )
