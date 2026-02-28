from typing import TYPE_CHECKING

from imgtests.exec.loaders import Perf
from imgtests.runner import AbstractRunnableManyTimesTest

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


class SchedPerformanceTest(AbstractRunnableManyTimesTest):
    def __init__(self, iterations: int = 1) -> None:
        super().__init__("Benchmark scheduler and IPC mechanisms.", {"IPC"}, iterations)

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        iterations: int,
    ) -> None:
        perf = Perf(client)
        for benchmark, args in zip(
            ["messaging", "messaging", "pipe"], [[], ["--thread"], []], strict=True
        ):
            _, m = perf.bench("sched", benchmark, args, repeat=iterations)
            self.logger.info(
                "Total time: %s. For the benchmark '%s' with args %s.",
                m[0].total_time,
                benchmark,
                str(args),
            )
