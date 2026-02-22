import logging
from typing import TYPE_CHECKING, Any, Literal, get_args

from imgtests.exec.loaders.perf import Perf
from imgtests.exec.loaders.pts import PhoronixTestSuite

if TYPE_CHECKING:
    from imgtests.database.database import ImgtestsDatabase
    from imgtests.exec.exec import SSHClient

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
            "network": [
                "pts/network-loopback",
            ],
            "memory": [
                "pts/tinymembench",
            ],
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
            "memory": [
                "mem",
            ],
            "ipc": [
                "sched",
            ],
            "syscalls": [
                "syscall",
            ],
        },
    },
}

Subsystem = Literal[
    "cpu",
    "disk",
    "memory",
    "network",
    "ipc",
    "syscalls",
    "system",
]


class JointBench:
    def __init__(self, database: ImgtestsDatabase, ssh_client: SSHClient | None = None):
        self.ssh_client = ssh_client
        self.logger = logging.getLogger()
        self.__database = database
        self.tools = {}
        for tool_name, config in TOOLS_CONFIG.items():
            self.tools[tool_name] = config["class"](self.ssh_client)

    def run(self, target: Subsystem):
        if target not in get_args(Subsystem):
            err_msg = f"Invalid action '{target}'. Expected one of {get_args(Subsystem)}."
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
        pass
