import logging

from imgtests.exec.exec import SSHClient
from imgtests.exec.observers.dd import Dd
from imgtests.exec.observers.time import Time
from imgtests.exec.observers.rm import Rm

logger = logging.getLogger(__name__)

def run_all_tests(client: SSHClient | None, iterations: int):
    test_utils_for_files(client, iterations)
    test_utils_for_dirs(client, iterations)
    test_net_utils(client, iterations)
    test_other_tools(client, iterations)

def test_utils_for_files(client: SSHClient | None, iterations: int) -> None:
    logger.info("Testing standard utilities for working with files...")
    time = Time(client)
    dd = Dd(client)
    filename1 = "/tmp/test_file1"
    filename2 = "/tmp/test_file2"
    ret = dd(
        [
            "if=/dev/urandom",
            "bs=1M",
            "count=50",
            "|",
            "tr",
            "-dc",
            "'[:print:]'",
            ">",
            filename1,
            "2>/dev/null",
        ]
    )
    if ret.returncode:
        logger.error("Test file wasn't created correctly")
        return
    ret = dd(
        [
            "if=/dev/urandom",
            "bs=1M",
            "count=50",
            "|",
            "tr",
            "-dc",
            "'[:print:]'",
            ">",
            filename2,
            "2>/dev/null",
        ]
    )
    if ret.returncode:
        logger.error("Test file wasn't created correctly")
        return
    tools = [
        "cat",
        "head",
        "tail",
        "wc",
        "od",
        "md5sum",
        "sha56sum",
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
    for i in range(iterations):
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
                cmd = " ".join([tool, filename1, f"{filename1}.copy"])
            elif tool == "patch":
                cmd = f"{tool} {filename1}.copy < diff.patch"
            elif tool == "mv":
                cmd = " ".join([tool, f"{filename1}.copy", f"{filename1}.new"])
            elif tool == "ln":
                cmd = " ".join([tool, filename1, f"{filename1}.hardlink"])
            elif tool == "rm":
                cmd = " ".join([tool, f"{filename1}.new", f"{filename1}.hardlink"])
            elif tool == "chmod":
                cmd = f"{tool} 777 {filename1}"
            elif tool in {"chown", "chgrp"}:
                cmd = f"{tool} root {filename1}"
            elif tool == "tar":
                cmd = f"{tool} cf {filename1}.tar {filename1}"
            ret = time([cmd, ">", "/dev/null"])
            logger.info(
                "Results for %s benchmarking: %s",
                tool,
                ret.stdout,
            )


def test_net_utils(client: SSHClient | None, iterations: int) -> None:
    logger.info("Testing standard network utilities...")
    time = Time(client)
    tools = [
        "ping",
        "netstat"
    ]
    for i in range(iterations):
        for tool in tools:
            cmd = tool
            if tool == "ping":
                cmd = f"{tool} 8.8.8.8"
            ret = time([cmd, ">", "/dev/null"])
            logger.info(
                "Results for %s benchmarking: %s",
                tool,
                ret.stdout,
            )


def test_utils_for_dirs(client: SSHClient | None, iterations: int) -> None:
    logger.info("Testing standard utilities for working with directories...")
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
    path = "/tmp/" + "/".join(str(i) for i in range(1, 51))
    for i in range(iterations):
        for tool in tools:
            cmd = tool
            if tool in {"mkdir", "rmdir"}:
                cmd = f"{tool} -p {path}"
            elif tool == "find":
                cmd = f"{tool} /tmp -type d -name '40'"
            elif tool == "ls":
                for i in range(1, 101):
                    dd(["if=/dev/urandom", f"of=/tmp/file{i}", "bs=10", "count=1", "2>/dev/null"])
                cmd = f"{tool} /tmp"
                rm(["/tmp/file*"])
            elif tool == "realpath":
                cmd = f"{tool} {path}"
            ret = time([cmd, ">", "/dev/null"])
            logger.info(
                "Results for %s benchmarking: %s",
                tool,
                ret.stdout,
            )


def test_other_tools(client: SSHClient | None, iterations: int) -> None:
    logger.info("Testing other utilities...")
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
    process = "init"
    for i in range(iterations):
        for tool in tools:
            cmd = tool
            if tool == "ps":
                cmd = f"{tool} aux | grep {process}"
            elif tool == "pgrep":
                cmd = f"{tool} {process}"
            elif tool in {"echo", "hello"}:
                string = "a" * 1000
                cmd = f"{tool} {string}"
            ret = time([cmd, ">", "/dev/null"])
            logger.info(
                "Results for %s benchmarking: %s",
                tool,
                ret.stdout,
            )
