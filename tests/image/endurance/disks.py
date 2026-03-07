from typing import TYPE_CHECKING

from imgtests.exec.loaders import StressNg
from imgtests.suites.drive.stress_ng import StressNgTest

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


class StressNgEnduranceDisksTest(StressNgTest):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Stress-ng endurance disks test.",
            {"file"},
            timeout,
        )

    def _run(self, executor: ThreadPoolExecutor, client: SSHClient | None, timeout: int) -> None:
        stress_ng = StressNg(client)
        params = {"hdd": 1, "hdd_bytes": "100M", "hdd_opts": "sync"}
        self.run_test(stress_ng=stress_ng, executor=executor, timeout=timeout, **params)
