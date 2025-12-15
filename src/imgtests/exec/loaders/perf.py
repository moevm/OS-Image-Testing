import logging
import re
from typing import NamedTuple

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient

logger = logging.getLogger(__name__)


class PerfBenchMetrics(NamedTuple):
    benchmark: str
    total_time: float
    usecs_per_op: float
    ops_per_sec: int


class Perf(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("perf", ssh_client)

    def stat(self, cmd: list[str]) -> ExecResult:
        return self(["stat", "--json", *cmd])

    def bench(self, cmd: list[str]) -> ExecResult:
        return self(["bench", *cmd])

    def _parse_bench(self, result: str) -> list[PerfBenchMetrics]:
        total_time_pattern = re.compile(r"Total time:\s*([\d.]+)")
        usecs_per_op_pattern = re.compile(r"([\d.]+)\s*usecs/op")
        ops_per_sec_pattern = re.compile(r"(\d+)\s*ops/sec")
        benchmark_name_pattern = re.compile(r"# Running\s*(.*?)\s*benchmark...")
        lines = result.splitlines()
        results: list[PerfBenchMetrics] = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            benchmark_match = benchmark_name_pattern.match(line)
            if benchmark_match:
                benchmark_name = benchmark_match.group(1).strip()
                time_match = None
                usecs_match = None
                ops_match = None
                i += 1
                while i < len(lines) and not lines[i].startswith("# Running"):
                    current_line = lines[i].strip()
                    if current_line.startswith("Total time:"):
                        time_match = total_time_pattern.search(current_line)
                    elif "usecs/op" in current_line:
                        usecs_match = usecs_per_op_pattern.search(current_line)
                    elif "ops/sec" in current_line:
                        ops_match = ops_per_sec_pattern.search(current_line)
                    i += 1
                usecs_per_op = float(usecs_match.group(1)) if usecs_match else -1
                ops_per_sec = int(ops_match.group(1)) if ops_match else -1
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
                data = PerfBenchMetrics(benchmark_name, total_time, usecs_per_op, ops_per_sec)
                results.append(data)
            else:
                i += 1
        return results
