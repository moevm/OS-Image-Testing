import re
from pathlib import Path
from imgtests.exec.base_util import BaseTestUtil
from imgtests.exec.exec import SSHClient


class Parser(BaseTestUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("parser", ssh_client)

    def stat(self, lines: list[str]) -> dict:
        result = {}
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r"^\s*([\d.]+)\s+seconds\s+(user|sys)\s*$", line)
            if m:
                value, key = float(m.group(1)), m.group(2)
                result[key] = value
                continue
            m = re.match(r"^\s*([\d,.]+)\s+\w+\s+([^\s#]+)", line)
            if m:
                value_str, metric = m.group(1).replace(",", ""), m.group(2)
                try:
                    value = int(value_str)
                except ValueError:
                    value = float(value_str)
                result[metric] = value
                continue
            m = re.match(r"^\s*([\d,.]+)\s+([^\s#]+)", line)
            if m:
                value_str, metric = m.group(1).replace(",", ""), m.group(2)
                try:
                    value = int(value_str)
                except ValueError:
                    value = float(value_str)
                result[metric] = value
        return result

    def bench(self, lines: list[str]) -> dict:
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
