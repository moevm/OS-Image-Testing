import logging
import shlex
from typing import TYPE_CHECKING, Final

from imgtests.exec.exec import SSHClient, common_run_command
from imgtests.exec.loaders import StressNg
from imgtests.runner import AbstractRunnableTimeLimitedTest
from imgtests.suites.general.stress_ng import StressNgTest

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

_GOOGLE_URL: Final = shlex.quote("http://142.250.185.206/")
_DNS_SERVER: Final = shlex.quote("8.8.8.8")


class StressNgEnduranceNetworkTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Stress-ng endurance network test.",
            {"network"},
            timeout,
        )

    def _run(self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int) -> None:
        stress_ng = StressNg(client)
        self.run_test(
            stress_ng=stress_ng,
            executor=executor,
            timeout=timeout,
            sock=2,
            sock_ops=2,
        )


class WgetEnduranceNetworkTest(AbstractRunnableTimeLimitedTest):
    def __init__(self, timeout: int) -> None:
        super().__init__("Load CPU 70% with chaosblade.", {"network"}, timeout)

    def _run(self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int) -> None:
        def run_test() -> None:
            if common_run_command(
                ["echo", "nameserver", _DNS_SERVER, ">>", "/etc/resolv.conf"], client
            ).returncode:
                self.logger.error("NETWORK endurance test FAILED")
                return
            result = common_run_command(
                ["wget", f"--timeout={timeout}", "--tries=1", _GOOGLE_URL],
                client,
            )
            if result.returncode:
                self.logger.error("NETWORK endurance test FAILED")
                return
            self.logger.info("NETWORK endurance test PASSED")

        future = executor.submit(run_test)
        future.result()
