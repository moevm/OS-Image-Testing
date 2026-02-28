import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

from imgtests.exec.exec import common_run_command
from imgtests.runner import AbstractRunnableManyTimesTest

if TYPE_CHECKING:
    from concurrent.futures import Future, ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient

import numpy as np
import numpy.typing as npt

from imgtests.exec.observers.time import Time, Times
from imgtests.exec.user_commands import Dd, Rm


class ToolTimes(NamedTuple):
    mean: npt.NDArray[np.float64]
    median: npt.NDArray[np.float64]
    std: npt.NDArray[np.float64]
    var: npt.NDArray[np.float64]


Tool = str
ToolsTimes = dict[str, ToolTimes | None]


class POSIXUtilsTest(AbstractRunnableManyTimesTest):
    def __init__(self, iterations: int = 1) -> None:
        super().__init__("Tests standard utilities performance.", {"system"}, iterations)

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        iterations: int,
    ) -> None:
        final_results: ToolsTimes = {}
        net_results = self.test_net_utils(executor, client, iterations)
        files_results = self.test_utils_for_files(client, iterations)
        dirs_results = self.test_utils_for_dirs(client, iterations)
        other_results = self.test_other_tools(client, iterations)
        final_results.update(net_results)
        final_results.update(files_results)
        final_results.update(dirs_results)
        final_results.update(other_results)

    def test_utils_for_files(  # noqa: PLR0912, C901
        self, client: SSHClient | None, iterations: int
    ) -> ToolsTimes:
        time = Time(client)
        dd = Dd(client)
        tmpdir = Path(tempfile.gettempdir())
        filename1 = tmpdir / "test_file1"
        filename2 = tmpdir / "test_file2"
        ret = dd(
            [
                "if=/dev/urandom",
                "bs=1M",
                "count=50",
                f"of={filename1}",
            ]
        )
        common_run_command(["strings", str(filename1), ">", str(filename1)], client)
        if ret.returncode:
            self.logger.error("Test file wasn't created correctly")
            return {}
        ret = dd(
            [
                "if=/dev/urandom",
                "bs=1M",
                "count=50",
                f"of={filename2}",
            ]
        )
        common_run_command(["strings", str(filename2), ">", str(filename2)], client)
        if ret.returncode:
            self.logger.error("Test file wasn't created correctly")
            return {}
        tools = [
            "cat",
            "head",
            "tail",
            "wc",
            "od",
            "md5sum",
            "sha256sum",
            "sort",
            "uniq",
            "grep",
            "paste",
            "tr",
            "diff",
            "patch",
            "cp",
            "rm",
            "mv",
            "ln",
            "chmod",
            "chown",
            "chgrp",
            "tar",
        ]
        results: ToolsTimes = {}
        for tool in tools:
            cmd = tool
            if tool in {"head", "tail"}:
                cmd = f"{tool} -n 1000 {filename1}"
            elif tool == "grep":
                cmd = f"{tool} test {filename1}"
            elif tool == "paste":
                cmd = f"{tool} {filename2} {filename1}"
            elif tool == "tr":
                cmd = f"{tool} 'a-z' 'A-Z' < {filename1}"
            elif tool == "diff":
                cmd = f"{tool} -u {filename1} {filename2} > diff.patch"
            elif tool == "cp":
                cmd = " ".join([tool, str(filename1), f"{filename1}.copy"])
            elif tool == "patch":
                cmd = f"{tool} {filename1}.copy < diff.patch"
            elif tool == "mv":
                cmd = " ".join([tool, f"{filename1}.copy", f"{filename1}.new"])
            elif tool == "ln":
                cmd = " ".join([tool, str(filename1), f"{filename1}.hardlink"])
            elif tool == "rm":
                cmd = " ".join([tool, f"{filename1}.new", f"{filename1}.hardlink"])
            elif tool == "chmod":
                cmd = f"{tool} 777 {filename1}"
            elif tool in {"chown", "chgrp"}:
                cmd = f"{tool} root {filename1}"
            elif tool == "tar":
                cmd = f"{tool} cf {filename1}.tar {filename1}"
            elif tool in {"md5sum", "sha256sum"}:
                cmd = f"dd if=/dev/zero bs=1M count=1024 | {tool}"
            results[tool] = time_cmd_many(time, cmd, iterations)
            self.logger.info("Results for %s: %s", tool, time_cmd_many(time, cmd, iterations))
        return results

    def test_net_utils(
        self, executor: ThreadPoolExecutor, client: SSHClient | None, iterations: int
    ) -> ToolsTimes:
        time = Time(client)
        tools = ["netstat", "lsof", "ping"]
        results: ToolsTimes = {}
        futures: list[Future[ToolTimes | None]] = []
        for tool in tools:
            cmd = tool
            if tool == "ping":
                cmd = f"{tool} -c 20 localhost"
            futures.append(executor.submit(time_cmd_many, time, cmd, iterations))
        for i, future in enumerate(futures):
            tool = tools[i]
            result = future.result()
            results[tool] = result
            self.logger.info("Results for %s: %s", tool, results[tool])
        return results

    def test_utils_for_dirs(self, client: SSHClient | None, iterations: int) -> ToolsTimes:
        time = Time(client)
        dd = Dd(client)
        rm = Rm(client)
        tools = [
            "mkdir",
            "find",
            "ls",
            "du",
            "realpath",
            "rmdir",
        ]
        results: ToolsTimes = {}
        tmpdir = Path(tempfile.gettempdir())
        path = tmpdir / "/".join(str(i) for i in range(1, 51))
        for tool in tools:
            cmd = tool
            if tool in {"mkdir", "rmdir"}:
                cmd = f"{tool} -p {path}"
            elif tool == "find":
                cmd = f"{tool} /tmp -type d -name '40'"
            elif tool == "ls":
                for j in range(1, 101):
                    dd(["if=/dev/urandom", f"of=/tmp/file{j}", "bs=10", "count=1", "2>/dev/null"])
                cmd = f"{tool} /tmp"
                rm([str(tmpdir / "/file*")])
            elif tool == "realpath":
                cmd = f"{tool} {path}"
            results[tool] = time_cmd_many(time, cmd, iterations)
            self.logger.info("Results for %s: %s", tool, results[tool])
        return results

    def test_other_tools(self, client: SSHClient | None, iterations: int) -> ToolsTimes:
        time = Time(client)
        tools = [
            "ps",
            "pgrep",
            "echo",
            "printf",
            "id",
            "who",
            "whoami",
            "hostname",
            "uname",
            "date",
            "uptime",
            "df",
        ]
        results: ToolsTimes = {}
        process = "init"
        for tool in tools:
            cmd = tool
            if tool == "ps":
                cmd = f"{tool} aux | grep {process}"
            elif tool == "pgrep":
                cmd = f"{tool} {process}"
            elif tool in {"echo", "hello"}:
                string = "a" * 1000
                cmd = f"{tool} {string}"
            results[tool] = time_cmd_many(time, cmd, iterations)
            self.logger.info("Results for %s: %s", tool, results[tool])
        return results


def time_cmd_many(
    time: Time,
    tool: str,
    iterations: int,
) -> ToolTimes | None:
    result: list[Times] = []
    for _ in range(iterations):
        times = time.run(tool)
        if times is None:
            return None
        result.append(times)
    array = np.array(result, dtype=np.float64)
    return ToolTimes(
        array.mean(axis=0), np.median(array, axis=0), array.std(axis=0), array.var(axis=0)
    )
