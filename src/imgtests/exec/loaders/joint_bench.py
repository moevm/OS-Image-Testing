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
                {"test_name": "pts/core-latency", "run_count": 1},
            ],
            "disk": [
                {"test_name": "pts/hdparm-read", "run_count": 1},
            ],
            "network": [
                {"test_name": "pts/network-loopback", "run_count": 1},
            ],
            "memory": [
                {"test_name": "pts/tinymembench", "run_count": 1},
            ],
            "system": [
                {"test_name": "pts/ctx-clock", "run_count": 1},
                {"test_name": "pts/appleseed", "run_count": 1},
            ],
        },
    },
    "Perf bench": {
        "class": Perf,
        "run": "bench",
        "target": {
            "memory": [
                {"collection": "mem"},
            ],
            "ipc": [
                {"collection": "sched"},
            ],
            "syscalls": [
                {"collection": "syscall"},
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
    def __init__(self, ssh_client: SSHClient | None = None):
        self.ssh_client = ssh_client
        self.logger = logging.getLogger()
        self.tools = {}
        for tool_name, config in TOOLS_CONFIG.items():
            self.tools[tool_name] = config["class"](self.ssh_client)

    def run(self, target: Subsystem) -> list[dict[str, Any]]:
        if target not in get_args(Subsystem):
            err_msg = f"Invalid action '{target}'. Expected one of {get_args(Subsystem)}."
            raise ValueError(err_msg)

        result = []

        for tool_name, config in TOOLS_CONFIG.items():
            tool_instance = self.tools[tool_name]
            tests = config["target"].get(target, [])

            if tests:
                for test in tests:
                    run_method = getattr(tool_instance, config["run"])
                    self.logger.info("Run '%s' test '%s'", tool_name, test)
                    tool_result, metrics = run_method(**test)

                    metrics_json = tool_instance.serialize_metrics(metrics)
                    result.append(
                        {
                            "result": metrics_json,
                            "command": " ".join(tool_result.cmd),
                        }
                    )
        return result

    def save(self, db: ImgtestsDatabase, result: list[dict[str, Any]], experiment_id: int):
        for tool_result in result:
            db.insert_loader(
                experiment_id=experiment_id,
                **tool_result,
            )
