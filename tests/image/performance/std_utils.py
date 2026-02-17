import logging
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from imgtests.exec.exec import SSHClient
from imgtests.exec.observers.time import Time
from imgtests.exec.user_commands import Dd, Rm

logger = logging.getLogger(__name__)


def test_all_tools(executor: ThreadPoolExecutor, client: SSHClient | None, iterations: int):
    samples = test_net_utils(executor, client, iterations)
    for tool in samples:
        real, user, system = [], [], []
        for result in samples[tool]:
            parts = list(map(float, result.split()))
            real.append(parts[0])
            user.append(parts[1])
            system.append(parts[2])
        r_mean = np.mean(real)
        r_median = np.median(real)
        r_std = np.std(real)
        r_var = np.var(real)
        u_mean = np.mean(user)
        u_median = np.median(user)
        u_std = np.std(user)
        u_var = np.var(user)
        s_mean = np.mean(system)
        s_median = np.median(system)
        s_std = np.std(system)
        s_var = np.var(system)
        logger.info(
            "Results for %s: \
            real time: %s, mean = %f, median = %f, variance = %f, standard deviation = %f\n \
            user time: %s, mean = %f, median = %f, variance = %f, standard deviation = %f\n \
            system time: %s, mean = %f, median = %f, variance = %f, standard deviation = %f",
            tool,
            real,
            r_mean,
            r_median,
            r_var,
            r_std,
            user,
            u_mean,
            u_median,
            u_var,
            u_std,
            system,
            s_mean,
            s_median,
            s_var,
            s_std,
        )
    samples = test_utils_for_files(executor, client, iterations)
    for tool in samples:
        real, user, system = [], [], []
        for result in samples[tool]:
            parts = result.split()
            real.append(parts[0])
            user.append(parts[1])
            system.append(parts[2])
        r_mean = np.mean(real)
        r_median = np.median(real)
        r_std = np.std(real)
        r_var = np.var(real)
        u_mean = np.mean(user)
        u_median = np.median(user)
        u_std = np.std(user)
        u_var = np.var(user)
        s_mean = np.mean(system)
        s_median = np.median(system)
        s_std = np.std(system)
        s_var = np.var(system)
        logger.info(
            "Results for %s: \
            real time: %s, mean = %f, median = %f, variance = %f, standard deviation = %f\n \
            user time: %s, mean = %f, median = %f, variance = %f, standard deviation = %f\n \
            system time: %s, mean = %f, median = %f, variance = %f, standard deviation = %f",
            tool,
            real,
            r_mean,
            r_median,
            r_var,
            r_std,
            user,
            u_mean,
            u_median,
            u_var,
            u_std,
            system,
            s_mean,
            s_median,
            s_var,
            s_std,
        )
    samples = test_utils_for_dirs(executor, client, iterations)
    for tool in samples:
        real, user, system = [], [], []
        for result in samples[tool]:
            parts = result.split()
            real.append(parts[0])
            user.append(parts[1])
            system.append(parts[2])
        r_mean = np.mean(real)
        r_median = np.median(real)
        r_std = np.std(real)
        r_var = np.var(real)
        u_mean = np.mean(user)
        u_median = np.median(user)
        u_std = np.std(user)
        u_var = np.var(user)
        s_mean = np.mean(system)
        s_median = np.median(system)
        s_std = np.std(system)
        s_var = np.var(system)
        logger.info(
            "Results for %s: \
            real time: %s, mean = %f, median = %f, variance = %f, standard deviation = %f\n \
            user time: %s, mean = %f, median = %f, variance = %f, standard deviation = %f\n \
            system time: %s, mean = %f, median = %f, variance = %f, standard deviation = %f",
            tool,
            real,
            r_mean,
            r_median,
            r_var,
            r_std,
            user,
            u_mean,
            u_median,
            u_var,
            u_std,
            system,
            s_mean,
            s_median,
            s_var,
            s_std,
        )
    samples = test_other_tools(executor, client, iterations)
    for tool in samples:
        real, user, system = [], [], []
        for result in samples[tool]:
            parts = result.split()
            real.append(parts[0])
            user.append(parts[1])
            system.append(parts[2])
        r_mean = np.mean(real)
        r_median = np.median(real)
        r_std = np.std(real)
        r_var = np.var(real)
        u_mean = np.mean(user)
        u_median = np.median(user)
        u_std = np.std(user)
        u_var = np.var(user)
        s_mean = np.mean(system)
        s_median = np.median(system)
        s_std = np.std(system)
        s_var = np.var(system)
        logger.info(
            "Results for %s:\n \
            real time: %s, mean = %f, median = %f, variance = %f, standard deviation = %f\n \
            user time: %s, mean = %f, median = %f, variance = %f, standard deviation = %f\n \
            system time: %s, mean = %f, median = %f, variance = %f, standard deviation = %f",
            tool,
            real,
            r_mean,
            r_median,
            r_var,
            r_std,
            user,
            u_mean,
            u_median,
            u_var,
            u_std,
            system,
            s_mean,
            s_median,
            s_var,
            s_std,
        )


def test_utils_for_files(
    _: ThreadPoolExecutor, client: SSHClient | None, iterations: int
) -> dict[str, list[str]]:
    logger.info("Testing standard utilities for working with files...")
    time = Time(client)
    dd = Dd(client)
    filename1 = "/tmp/test_file1"
    filename2 = "/tmp/test_file2"
    ret = dd(
        [
            "if=/dev/urandom",
            "bs=1M",
            "count=10",
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
        return {}
    ret = dd(
        [
            "if=/dev/urandom",
            "bs=1M",
            "count=10",
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
    results = [[] for tool in tools]
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
            elif tool in {"md5sum", "sha256sum"}:
                cmd = f"dd if=/dev/zero bs=1M count=1024 | {tool}"
            ret = time(["-f", "'%e %U %S'", cmd, ">", "/dev/null"])
            results[tools.index(tool)].append(ret.stderr)
    return dict(zip(tools, results, strict=True))


def test_net_utils(
    _: ThreadPoolExecutor, client: SSHClient | None, iterations: int
) -> dict[str, list[str]]:
    logger.info("Testing standard network utilities...")
    time = Time(client)
    tools = ["ping", "netstat"]
    results = [[] for tool in tools]
    for i in range(iterations):
        for tool in tools:
            cmd = tool
            if tool == "ping":
                cmd = f"{tool} -c 5 8.8.8.8"
            ret = time(["-f", "'%e %U %S'", cmd])
            results[tools.index(tool)].append(ret.stderr)
    return dict(zip(tools, results, strict=True))


def test_utils_for_dirs(
    _: ThreadPoolExecutor, client: SSHClient | None, iterations: int
) -> dict[str, list[str]]:
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
    results = [[] for tool in tools]
    path = "/tmp/" + "/".join(str(i) for i in range(1, 51))
    for i in range(iterations):
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
                rm(["/tmp/file*"])
            elif tool == "realpath":
                cmd = f"{tool} {path}"
            ret = time(["-f", "'%e %U %S'", cmd, ">", "/dev/null"])
            results[tools.index(tool)].append(ret.stderr)
    return dict(zip(tools, results, strict=True))


def test_other_tools(
    _: ThreadPoolExecutor, client: SSHClient | None, iterations: int
) -> dict[str, list[str]]:
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
    results = [[] for tool in tools]
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
            ret = time(["-f", "'%e %U %S'", cmd, ">", "/dev/null"])
            results[tools.index(tool)].append(ret.stderr)
    return dict(zip(tools, results, strict=True))
