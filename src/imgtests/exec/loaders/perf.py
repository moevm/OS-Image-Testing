import json
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
    total_time: float | None = None
    usecs_per_op: float | None = None
    ops_per_sec: int | None = None
    gb_per_sec_default: float | None = None
    gb_per_sec_unrolled: float | None = None
    gb_per_sec_movsq_based: float | None = None


TOTAL_TIME_PATTERN: Final = re.compile(r"\s*Total time:\s*([\d.]+)")
USECS_PER_OP_PATTERN: Final = re.compile(r"^\s*([\d,.\s]+)\s*usecs/op")
OPS_PER_SEC_PATTERN: Final = re.compile(r"\s*(\d+)\s*ops/sec")
BENCHMARK_NAME_PATTERN: Final = re.compile(r"# Running (?:')?(.*?)(?:')? benchmark")
GB_PER_SEC_PATTERN: Final = re.compile(r"^\s*([\d,.\s]+)\s*GB/sec")
FUNCTION_PATTERNS: Final = {
    "default": re.compile(r"# function.*Default"),
    "unrolled": re.compile(r"# function.*unrolled"),
    "movsq": re.compile(r"# function.*movsq-based"),
}


class Perf(PkgMgrMixin, GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("perf", ssh_client)

    def install(self) -> ExecResult:
        """Install perf via the system package manager."""
        if self.path:
            return ExecResult(
                cmd=(), stderr=f"{self.name} already has been installed.", returncode=0
            )
        return self._install_packages(["perf"])

    def stat(self, cmd: list[str]) -> ExecResult:
        return self(["stat", "--json", *cmd])

    def bench(
        self,
        collection: str = "all",
        benchmark: str = "all",
        add_opts: list[str] | None = None,
        format_: Literal["default", "simple"] = "default",
        repeat: int = 1,
    ) -> tuple[ExecResult, tuple[PerfBenchMetrics, ...]]:
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

        return result, self.parse_bench(result.stdout.strip())

    @staticmethod
    def parse_bench(result: str) -> tuple[PerfBenchMetrics, ...]:  # noqa: PLR0912 PLR0915 C901
        lines = [line.strip() for line in result.splitlines() if line.strip()]
        results: list[PerfBenchMetrics] = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            benchmark_match = BENCHMARK_NAME_PATTERN.match(line)
            if not benchmark_match:
                i += 1
                continue
            benchmark_name = benchmark_match.group(1).strip()
            time_match = None
            usecs_match = None
            ops_match = None
            gb_match = None
            total_time = None
            usecs_per_op = None
            ops_per_sec = None
            gb_default = None
            gb_unrolled = None
            gb_movsq = None
            i += 1
            while i < len(lines) and not lines[i].startswith("# Running"):
                current_line = lines[i].strip()
                if current_line.startswith("Total time:"):
                    time_match = TOTAL_TIME_PATTERN.search(current_line)
                    if time_match:
                        total_time = float(time_match.group(1).replace(",", "."))
                    else:
                        logger.warning("Failed to parse total time line")

                elif "usecs/op" in current_line:
                    usecs_match = USECS_PER_OP_PATTERN.search(current_line)
                    if usecs_match:
                        usecs_per_op = float(usecs_match.group(1).replace(",", "."))
                    else:
                        logger.warning("Failed to parse usecs/op line")

                elif "ops/sec" in current_line:
                    ops_match = OPS_PER_SEC_PATTERN.search(current_line)
                    if ops_match:
                        ops_per_sec = int(ops_match.group(1))
                    else:
                        logger.warning("Failed to parse ops/sec line")

                else:
                    for func_name, func_pat in FUNCTION_PATTERNS.items():
                        if not func_pat.search(current_line):
                            continue
                        gb_line_idx = i + 2
                        if gb_line_idx >= len(lines):
                            break
                        gb_line = lines[gb_line_idx]
                        gb_match = GB_PER_SEC_PATTERN.search(gb_line)
                        if gb_match:
                            gb_value = float(gb_match.group(1).replace(",", "."))
                            if func_name == "default":
                                gb_default = gb_value
                            elif func_name == "unrolled":
                                gb_unrolled = gb_value
                            elif func_name == "movsq":
                                gb_movsq = gb_value
                        else:
                            logger.warning("Failed to parse GB/sec line for '%s'", func_name)
                i += 1

            results.append(
                PerfBenchMetrics(
                    benchmark_name,
                    total_time,
                    usecs_per_op,
                    ops_per_sec,
                    gb_default,
                    gb_unrolled,
                    gb_movsq,
                )
            )
        return tuple(results)

    @staticmethod
    def serialize_metrics(result: tuple[PerfBenchMetrics, ...]) -> str:
        processed_result = []
        for metrics in result:
            d = metrics._asdict()
            filtered_d = {key: value for key, value in d.items() if value is not None}
            processed_result.append(filtered_d)

        return json.dumps(processed_result)
