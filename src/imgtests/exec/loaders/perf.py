from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient
import re

class Perf(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("perf", ssh_client)

    def stat(self, cmd: list[str]) -> ExecResult:
        return self(["stat", "--json", *cmd])

    def bench(self, cmd: list[str]) -> ExecResult:
        return self(["bench", *cmd])

    def _parse_bench(self, result: str) -> dict[str, int | float]:
        lines = result.splitlines()
        results = {}
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("# Running"):
                benchmark_name = line.replace("# Running", "").replace("benchmark...", "").strip()
                benchmark_data = {}
                i += 1
                while i < len(lines) and not lines[i].startswith("# Running"):
                    current_line = lines[i].strip()
                    if current_line.startswith("Total time:"):
                        time_match = re.search(r"Total time:\s*([\d.]+)", current_line)
                        if time_match:
                            benchmark_data["Total time"] = float(time_match.group(1))
                    elif "usecs/op" in current_line:
                        usecs_match = re.search(r"([\d.]+)\s*usecs/op", current_line)
                        if usecs_match:
                            benchmark_data["usecs/op"] = float(usecs_match.group(1))
                    elif "ops/sec" in current_line:
                        ops_match = re.search(r"(\d+)\s*ops/sec", current_line)
                        if ops_match:
                            benchmark_data["ops/sec"] = int(ops_match.group(1))
                    i += 1
                results[benchmark_name] = benchmark_data
            else:
                i += 1
        return results
