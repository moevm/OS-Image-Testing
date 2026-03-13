from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from imgtests.exec.loaders import Perf
from imgtests.runner import AbstractRunnableManyTimesTest, Subsystem, TestResult

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


class SchedPerformanceTest(AbstractRunnableManyTimesTest):
    def __init__(self, iterations: int = 1) -> None:
        super().__init__(
            "Benchmark scheduler and IPC mechanisms.", frozenset({Subsystem.IPC}), iterations
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        iterations: int,
    ) -> Iterable[TestResult]:
        perf = Perf(client)
        for benchmark, args in zip(
            ["messaging", "messaging", "pipe"], [[], ["--thread"], []], strict=True
        ):
            started_at = datetime.now(tz=ZoneInfo("UTC"))
            result, metrics = perf.bench("sched", benchmark, args, repeat=iterations)
            if result.returncode:
                self.logger.error("Failed to run benchmark '%s' with args '%s'.", benchmark, args)
            else:
                yield TestResult(
                    started_at=started_at,
                    metrics=perf.metrics_to_json(metrics),
                    command=" ".join(result.cmd),
                )


def perf_bench_result_to_bmf(output: list[str], benchmarks: list[tuple[str, list[str]]]) -> dict:
    result = {"sched": {}}

    for i, (bench_name, args) in enumerate(benchmarks):
        key = f"{bench_name} {' '.join(args)}" if args else bench_name
        try:
            value = float(output[i])
        except ValueError:
            value = 0.0

        result["sched"][key] = {"value": value}

    return result
