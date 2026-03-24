import logging
import shlex
from datetime import datetime
from typing import TYPE_CHECKING, Final
from zoneinfo import ZoneInfo

from imgtests.exec.exec import SSHClient, common_run_command
from imgtests.exec.loaders import StressNg
from imgtests.runner import AbstractRunnableTimeLimitedTest, Subsystem, TestResult, TestStatus
from imgtests.suites.general.stress_ng import StressNgTest

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

_GOOGLE_URL: Final = shlex.quote("http://142.250.185.206/")
_DNS_SERVER: Final = shlex.quote("8.8.8.8")


class StressNgEnduranceNetworkTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Stress-ng endurance network test.",
            frozenset({Subsystem.NETWORK}),
            timeout,
        )

    def _run(
        self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int
    ) -> Iterable[TestResult]:
        stress_ng = StressNg(client)
        yield from self.run_test(
            stress_ng=stress_ng,
            executor=executor,
            timeout=timeout,
            sock=2,
            sock_ops=2,
        )


class WgetEnduranceNetworkTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__("Load CPU 70% with chaosblade.", frozenset({Subsystem.NETWORK}), timeout)

    def _run(
        self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int
    ) -> Iterable[TestResult]:
        def run_test() -> int | None:
            if common_run_command(
                ["sudo", "echo", "nameserver", _DNS_SERVER, ">>", "/etc/resolv.conf"], client
            ).returncode:
                self.logger.error("NETWORK endurance test FAILED")
                return -1
            result = common_run_command(
                ["wget", f"--timeout={timeout}", "--tries=1", _GOOGLE_URL],
                client,
            )
            if result.returncode:
                self.logger.error("NETWORK endurance test FAILED")
                return -1
            self.logger.info("NETWORK endurance test PASSED")
            return None

        started_at = datetime.now(tz=ZoneInfo("UTC"))
        future = executor.submit(run_test)
        result = future.result()
        status = TestStatus.Failed
        if result is None:
            status = TestStatus.Passed
        yield TestResult(
            metrics=result,
            command=f"wget --timeout={timeout} --tries=1 {_GOOGLE_URL}",
            started_at=started_at,
            status=status,
        )
