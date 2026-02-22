import logging
from typing import Any, Literal, get_args

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
    "system",
]


class JointBench:
    def __init__(self):
        self.logger = logging.getLogger()
        self.tools = {}
        for tool_name, config in TOOLS_CONFIG.items():
            self.tools[tool_name] = config["class"]()

    def run(self, target: Target):
        if target not in get_args(Target):
            err_msg = f"Invalid action '{target}'. Expected one of {get_args(Target)}."
            raise ValueError(err_msg)

        for tool_name, config in TOOLS_CONFIG.items():
            tool_instance = self.tools[tool_name]
            tests = config["target"].get(target, [])

            if tests:
                for test in tests:
                    run_method = getattr(tool_instance, config["run"])
                    _, metrics = run_method(test)
                    self.logger.log("Run '%s' test '%s'", tool_name, test)
                    self.save(metrics)

    def save(self, json_metrics: dict[str, Any]):
        # log
        pass
