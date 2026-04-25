import logging
from typing import TYPE_CHECKING

from imgtests.exec.loaders import StressNg
from imgtests.suites.general.stress_ng import StressNgTest
from imgtests.types import Subsystem

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient
    from imgtests.runner import TestResult

logger = logging.getLogger(__name__)


class StressNgEnduranceNetworkTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Stress-ng endurance network test.",
            frozenset({Subsystem.NETWORK}),
            timeout,
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        stress_ng = StressNg(client)
        yield from self.run_test(
            stress_ng=stress_ng,
            executor=executor,
            timeout=timeout,
            sock=0,
            sock_ops=1000,
            netdev=0,
            udp=0,
        )
