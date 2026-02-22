from typing import Literal

from imgtests.exec.loaders.perf import Perf
from imgtests.exec.loaders.pts import PhoronixTestSuite

TOOLS_CONFIG = {
    "PTS": {
        "class": PhoronixTestSuite,
        "run": "run",
        "target": {
            "cpu": [
                "pts/core-latency",
            ],
            "disk": [
                "pts/hdparm-read",
            ],
            "network": ["pts/network-loopback"],
            "mem": ["pts/tinymembench"],
            "ipc": [],
            "syscalls": [],
            "system": [
                "pts/ctx-clock",
                "pts/appleseed",
            ],
        },
    },
    "Perf bench": {
        "class": Perf,
        "run": "bench",
        "target": {
            "cpu": [],
            "disk": [],
            "network": [],
            "mem": ["mem"],
            "ipc": [
                "sched",
            ],
            "syscalls": ["syscall"],
            "system": [],
        },
    },
}

Target = Literal[
    "cpu",
    "disk",
    "mem",
    "network",
    "ipc",
    "syscall",
    "system",  # or no????
]


class JointBench:
    pass
