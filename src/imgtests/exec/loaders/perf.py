import logging
import re
from typing import Final, Literal, NamedTuple

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient
from imgtests.exec.pkgmgrs.mixin import PkgMgrMixin
from imgtests.exec.utils import create_opt

logger = logging.getLogger(__name__)


class PerfBenchMetrics(NamedTuple):
    benchmark: str
    total_time: float
    usecs_per_op: float
    ops_per_sec: int


TOTAL_TIME_PATTERN: Final = re.compile(r"\s*Total time:\s*([\d.]+)")
USECS_PER_OP_PATTERN: Final = re.compile(r"\s*([\d.]+)\s*usecs/op")
OPS_PER_SEC_PATTERN: Final = re.compile(r"\s*(\d+)\s*ops/sec")
BENCHMARK_NAME_PATTERN: Final = re.compile(r"\s*# Running\s*(.*?)\s*benchmark...")


class Perf(PkgMgrMixin, GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("perf", ssh_client)

    def install(self) -> ExecResult:
        """Install perf via the system package manager."""
        return self._install_packages(["perf"])

    def stat(self, cmd: list[str]) -> ExecResult:
        return self(["stat", "--json", *cmd])

    def bench(
        self,
        collection: str = "all",
        benchmark: str = "all",
        add_opts: list[str] | None = None,
        format_: Literal["default", "simple"] = "simple",
        repeat: int = 1,
    ) -> ExecResult:
        """Runs benchmark suites.

        Args:
            collection (str): Testing subsystem. Default is "all".
            benchmark (str): Running tests. Default is "all".
            add_opts (list[str]): Additional tests options.
            format_: The output formatting style. Default is "simple".
            repeat (int): Number of times to repeat the run. Default is 1.
        """
        if repeat <= 0:
            err_msg = f"Invalid repeat value: {repeat}. Must be more than zero."
            raise ValueError(err_msg)
        if add_opts is None:
            add_opts = []

        result = self(
            [
                "bench",
                *create_opt("format", format_),
                *create_opt("repeat", repeat),
                collection,
                benchmark,
                *add_opts,
            ]
        )
        if result.returncode:
            return result
        return result

    @staticmethod
    def parse_bench(result: str) -> tuple[PerfBenchMetrics, ...]:  # noqa: PLR0912
        lines = [line.strip() for line in result.splitlines() if line.strip()]
        results: list[PerfBenchMetrics] = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            benchmark_match = BENCHMARK_NAME_PATTERN.match(line)
            if benchmark_match:
                benchmark_name = benchmark_match.group(1).strip()
                time_match = None
                usecs_match = None
                ops_match = None
                i += 1
                while i < len(lines) and not lines[i].startswith("# Running"):
                    current_line = lines[i].strip()
                    if current_line.startswith("Total time:"):
                        time_match = TOTAL_TIME_PATTERN.search(current_line)
                    elif "usecs/op" in current_line:
                        usecs_match = USECS_PER_OP_PATTERN.search(current_line)
                    elif "ops/sec" in current_line:
                        ops_match = OPS_PER_SEC_PATTERN.search(current_line)
                    i += 1
                if time_match:
                    total_time = float(time_match.group(1))
                else:
                    logger.warning("Failed to parse total time line")
                    total_time = -1
                if usecs_match:
                    usecs_per_op = float(usecs_match.group(1))
                else:
                    logger.warning("Failed to parse usecs/op line")
                    usecs_per_op = -1
                if ops_match:
                    ops_per_sec = int(ops_match.group(1))
                else:
                    logger.warning("Failed to parse ops/sec line")
                    ops_per_sec = -1
                results.append(
                    PerfBenchMetrics(benchmark_name, total_time, usecs_per_op, ops_per_sec)
                )
            else:
                i += 1
        return tuple(results)
