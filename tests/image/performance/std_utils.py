import tempfile
from concurrent.futures import as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Final, NamedTuple

from imgtests.exec.exec import common_run_command
from imgtests.runner import AbstractRunnableManyTimesTest, Subsystem

if TYPE_CHECKING:
    from concurrent.futures import Future, ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient

import numpy as np
import numpy.typing as npt

from imgtests.exec.observers.time import Time, Times
from imgtests.exec.user_commands import Dd, Rm

TEST_FILE1: Final = Path(tempfile.gettempdir()) / "test_file1"
TEST_FILE2: Final = Path(tempfile.gettempdir()) / "test_file2"


class ToolTimes(NamedTuple):
    mean: npt.NDArray[np.float64]
    median: npt.NDArray[np.float64]
    std: npt.NDArray[np.float64]
    var: npt.NDArray[np.float64]


Tool = str
ToolsTimes = dict[str, ToolTimes | None]


class POSIXUtilsTest(AbstractRunnableManyTimesTest):
    def __init__(self, iterations: int = 1) -> None:
        super().__init__(
            "Tests standard utilities performance.", frozenset({Subsystem.SYSTEM}), iterations
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        iterations: int,
    ) -> None:
        final_results: ToolsTimes = {}
        futures: list[Future[ToolsTimes]] = [
            executor.submit(func, client, iterations)
            for func in [
                self.test_net_utils,
                self.test_utils_for_files,
                self.test_utils_for_dirs,
                self.test_other_tools,
            ]
        ]
        for future in as_completed(futures):
            final_results.update(future.result())

    def test_utils_for_files(  # noqa: PLR0912, C901
        self, client: SSHClient | None, iterations: int
    ) -> ToolsTimes:
        time = Time(client)
        dd = Dd(client)
        ret = dd(
            [
                "if=/dev/urandom",
                "bs=1M",
                "count=50",
                f"of={TEST_FILE1}.tmp",
            ]
        )
        if ret.returncode:
            self.logger.error("Test file wasn't created correctly")
            return {}
        ret = common_run_command(
            ["tr", "-dc", "'[:print:]'", "<", f"{TEST_FILE1}.tmp", ">", str(TEST_FILE1)],
            client,
        )
        if ret.returncode:
            self.logger.error("Test file wasn't created correctly")
            return {}
        ret = dd(
            [
                "if=/dev/urandom",
                "bs=1M",
                "count=50",
                f"of={TEST_FILE2}.tmp",
            ]
        )
        if ret.returncode:
            self.logger.error("Test file wasn't created correctly")
            return {}
        ret = common_run_command(
            ["tr", "-dc", "'[:print:]'", "<", f"{TEST_FILE2}.tmp", ">", str(TEST_FILE2)],
            client,
        )
        if ret.returncode:
            self.logger.error("Test file wasn't created correctly")
            return {}
        common_run_command(["rm", "-f", f"{TEST_FILE1}.tmp", f"{TEST_FILE2}.tmp"], client)
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
            "cp",
            "patch",
            "mv",
            "ln",
            "rm",
            "chmod",
            "chown",
            "chgrp",
            "tar",
        ]
        results: ToolsTimes = {}
        for tool in tools:
            cmd = tool
            if tool in {"cat", "wc", "od", "sort", "uniq"}:
                cmd = f"cat {TEST_FILE1} {TEST_FILE2} > /dev/null"
            elif tool in {"head", "tail"}:
                cmd = f"{tool} -n 1000 {TEST_FILE1} {TEST_FILE2} > /dev/null"
            elif tool == "grep":
                cmd = f"bash -c '{tool} test {TEST_FILE1} {TEST_FILE2} > /dev/null || true'"
            elif tool == "paste":
                cmd = f"{tool} {TEST_FILE2} {TEST_FILE1} > /dev/null"
            elif tool == "tr":
                cmd = f"{tool} 'a-z' 'A-Z' < {TEST_FILE1} > /dev/null"
            elif tool == "diff":
                cmd = f"bash -c '{tool} -u {TEST_FILE1} {TEST_FILE2} > diff.patch || true'"
            elif tool == "cp":
                cmd = " ".join([tool, str(TEST_FILE1), f"{TEST_FILE1}.copy"])
            elif tool == "patch":
                cmd = f"{tool} {TEST_FILE1}.copy < diff.patch"
            elif tool == "mv":
                cmd = " ".join([tool, f"{TEST_FILE1}.copy", f"{TEST_FILE1}.new"])
            elif tool == "ln":
                cmd = " ".join([tool, str(TEST_FILE1), f"{TEST_FILE1}.hardlink"])
            elif tool == "rm":
                cmd = " ".join([tool, f"{TEST_FILE1}.new"])
            elif tool == "chmod":
                cmd = f"{tool} 777 {TEST_FILE1}"
            elif tool in {"chown", "chgrp"}:
                cmd = f"sudo {tool} root {TEST_FILE1}"
            elif tool == "tar":
                cmd = f"{tool} -cf {TEST_FILE1}.tar {TEST_FILE1}"
            elif tool in {"md5sum", "sha256sum"}:
                cmd = f"{tool} {TEST_FILE1} {TEST_FILE2}"
            results[tool] = time_cmd_many(time, cmd, iterations, client)
            self.logger.info("Results for %s: %s", tool, results[tool])
        return results

    def test_net_utils(self, client: SSHClient | None, iterations: int) -> ToolsTimes:
        time = Time(client)
        tools = ["netstat", "lsof", "ping"]
        results: ToolsTimes = {}
        for tool in tools:
            cmd = tool
            if tool == "ping":
                cmd = f"{tool} -c 20 localhost"
            results[tool] = time_cmd_many(time, cmd, iterations, client)
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
            if tool == "mkdir":
                cmd = f"{tool} -p {path}"
            elif tool == "rmdir":
                cmd = f"{tool} {tempfile.gettempdir()}/test"
            elif tool == "find":
                cmd = f"sudo {tool} /tmp -type d -name '40'"
            elif tool == "ls":
                for j in range(1, 101):
                    dd(["if=/dev/urandom", f"of=/tmp/file{j}", "bs=10", "count=1"])
                cmd = f"{tool} /tmp"
                rm([str(tmpdir / f"file{j}") for j in range(1, 101)])
            elif tool == "realpath":
                cmd = f"{tool} {path}"
            results[tool] = time_cmd_many(time, cmd, iterations, client)
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
                cmd = f"{tool} sh"
            elif tool in {"echo", "printf"}:
                string = "a" * 1000
                cmd = f"{tool} {string}"
            results[tool] = time_cmd_many(time, cmd, iterations)
            self.logger.info("Results for %s: %s", tool, results[tool])
        return results


def time_cmd_many(
    time: Time, tool: str, iterations: int, client: SSHClient | None = None
) -> ToolTimes | None:
    result: list[Times] = []
    for i in range(iterations):
        parts = tool.split()
        if "mkdir" in tool:
            common_run_command(
                [
                    "rm",
                    "-rf",
                    f"{tempfile.gettempdir()}/1",
                ],
                client,
            )
        elif "rmdir" in tool:
            common_run_command(["mkdir", f"{tempfile.gettempdir()}/test"], client)
        elif parts[0] == "patch":
            common_run_command(["cp", parts[1], f"{parts[1]}.{i}"], client)
            tool = f"{parts[0]} {parts[1]}.{i} < diff.patch"
        elif "mv" in tool:
            common_run_command(["cp", parts[1].split(".")[0], parts[1]], client)
        elif "ln" in tool:
            common_run_command(
                ["[", "-f", parts[2], "]", "&&", "rm", parts[2], "||", "true"], client
            )
        elif "rm" in tool:
            common_run_command(
                [
                    "[",
                    "!",
                    "-f",
                    parts[1],
                    "]",
                    "&&",
                    "cp",
                    parts[1].split(".")[0],
                    parts[1],
                    "||",
                    "true",
                ],
                client,
            )
        elif "tar" in tool:
            common_run_command(["rm", "-f", f"{TEST_FILE1}.tar"], client)
        times = time.run(tool)
        if times is None:
            return None
        result.append(times)
    array = np.array(result, dtype=np.float64)
    return ToolTimes(
        array.mean(axis=0), np.median(array, axis=0), array.std(axis=0), array.var(axis=0)
    )
