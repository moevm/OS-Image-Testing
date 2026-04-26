from copy import deepcopy
from datetime import datetime
from typing import TYPE_CHECKING, Any, NamedTuple
from zoneinfo import ZoneInfo

from imgtests.exec.loaders.perf import Perf
from imgtests.exec.loaders.pts import PhoronixTestSuite
from imgtests.planning import AbstractRunnableManyTimesTest
from imgtests.types import Subsystem, TestResult, TestStatus

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.base_util import BaseTestUtil
    from imgtests.exec.exec import ExecResult, SSHClient


class ToolConfig(NamedTuple):
    class_: type[PhoronixTestSuite | Perf]
    run: str
    subsystem: dict[Subsystem, tuple[dict[str, Any], ...]]


TOOLS_CONFIG: dict[str, ToolConfig] = {
    "PTS": ToolConfig(
        class_=PhoronixTestSuite,
        run="run",
        subsystem={
            Subsystem.FILE: ({"test_name": "pts/hdparm-read", "run_count": 1},),
            Subsystem.NETWORK: ({"test_name": "pts/network-loopback", "run_count": 1},),
            Subsystem.MEMORY: ({"test_name": "pts/tinymembench", "run_count": 1},),
            Subsystem.SYSTEM: (
                {"test_name": "pts/ctx-clock", "run_count": 1},
                {"test_name": "pts/appleseed", "run_count": 1},
            ),
        },
    ),
    "Perf bench": ToolConfig(
        class_=Perf,
        run="bench",
        subsystem={
            Subsystem.MEMORY: ({"collection": "mem"},),
            Subsystem.IPC: (
                {"collection": "sched", "benchmark": "messaging"},
                {"collection": "sched", "benchmark": "messaging", "add_opts": ["--thread"]},
                {"collection": "sched", "benchmark": "pipe"},
            ),
            Subsystem.SYSCALLS: ({"collection": "syscall"},),
        },
    ),
}


class JointBench(AbstractRunnableManyTimesTest):
    def __init__(
        self,
        subsystems: frozenset[Subsystem] = frozenset(
            {
                Subsystem.FILE,
                Subsystem.MEMORY,
                Subsystem.IPC,
                Subsystem.SYSCALLS,
                Subsystem.NETWORK,
                Subsystem.SYSTEM,
            },
        ),
        iterations: int = 1,
    ) -> None:
        super().__init__(
            "Run joint benchmark tests.",
            subsystems,
            iterations=iterations,
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        iterations: int,
    ) -> Iterable[TestResult]:
        self.tools: dict[str, BaseTestUtil] = {}
        for tool_name, config in TOOLS_CONFIG.items():
            self.tools[tool_name] = config.class_(client)
            self.logger.info("Preparing %s", tool_name)
            result = self.tools[tool_name].prepare()
            if result.returncode:
                self.logger.error("Failed to setup '%s' prepare.", tool_name)
                del self.tools[tool_name]

        result = []
        for tool_name in self.tools:
            tool_instance = self.tools[tool_name]
            for subsystem in self.subsystems:
                tests = TOOLS_CONFIG[tool_name].subsystem.get(subsystem, ())
                if not tests:
                    continue

                for test in tests:
                    test_copy = deepcopy(test)
                    match tool_name:
                        case "Perf bench":
                            test_copy["repeat"] = iterations
                        case "PTS":
                            test_copy["run_count"] = iterations
                        case _:
                            pass
                    run_method: Callable[..., tuple[ExecResult, Any]] = getattr(
                        tool_instance,
                        TOOLS_CONFIG[tool_name].run,
                    )
                    self.logger.info("Run '%s' test '%s'", tool_name, test_copy)
                    started_at = datetime.now(tz=ZoneInfo("UTC"))
                    # TODO: handle only specific exceptions
                    try:
                        tool_result, metrics = run_method(**test_copy)
                    except Exception:
                        self.logger.exception("Test failed.")
                        yield TestResult(status=TestStatus.BROKEN)
                        return
                    ended_at = datetime.now(tz=ZoneInfo("UTC"))
                    status = TestStatus.PASSED if not tool_result.returncode else TestStatus.FAILED
                    yield TestResult(
                        started_at=started_at,
                        ended_at=ended_at,
                        metrics=tool_instance.metrics_to_json(metrics),
                        command=" ".join(tool_result.cmd),
                        status=status,
                    )
