import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Thread
from typing import TYPE_CHECKING, Any, Literal, NamedTuple

import paramiko
import paramiko.ssh_exception

from imgtests.constant import LIB_NAME
from imgtests.database.database import ImgtestsDatabase
from imgtests.sysrep import get_system_info

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from imgtests.database.database import ExperimentType
    from imgtests.exec.base_util import BaseTestUtil
    from imgtests.exec.exec import SSHClient

Subsystem = Literal["file", "syscalls", "IPC", "network", "memory", "system"]


class RunnableTest:
    __slots__ = ("description", "iterations", "subsystems", "test_func")

    def __init__(
        self,
        description: str,
        subsystems: set[Subsystem],
        test_func: Callable[[ThreadPoolExecutor, SSHClient], None],
        iterations: int = 1,
    ) -> None:
        """Construct a RunnableTest instance.

        Initializes the runnable test with description, target subsystems,
        execution logic, and repetition parameters.

        Args:
            description: Test description.
            subsystems: Covered subsystems with the test.
            test_func: Test implementation.
            iterations: Count of test iterations to run. Defaults to 1.
        """
        self.description = description
        self.subsystems = subsystems
        self.test_func = test_func
        self.iterations = iterations

    def __call__(self, executor: ThreadPoolExecutor, client: SSHClient) -> Any:
        logger = logging.getLogger(f"{LIB_NAME}.runnable_test")
        logger.info(
            "Starting '%s' test '%d' times: '%s'.",
            self.test_func.__name__,
            self.iterations,
            self.description,
        )
        for _ in range(self.iterations):
            self.test_func(executor, client)
        logger.info("'%s' test finished.", self.test_func.__name__)


# Time to run, subsystems, stages (plan, risk analysis, run, cleanup, results, etc), etc
class TestsRunnerConfig(NamedTuple):
    description: str
    tests: Iterable[RunnableTest]
    experiment_type: ExperimentType
    install_dependencies: bool = False


class TestsRunner:
    __slots__ = ("__client", "__database", "__executor", "__test_config", "logger")

    def __init__(self, client: SSHClient, test_config: TestsRunnerConfig) -> None:
        self.__executor = ThreadPoolExecutor()
        self.__client = client
        self.__database = ImgtestsDatabase()
        self.__test_config = test_config
        self.logger = logging.getLogger(f"{LIB_NAME}.tests_runner")

    def run(self) -> None:
        test_completed_event = Event()
        if self.__test_config.install_dependencies:
            self.install_dependencies()
        result = get_system_info(self.__client)
        configuration_record = self.__database.insert_from_system_info(result)
        experiment = self.__database.insert_experiment(
            config_id=configuration_record.config_id,
            description=self.__test_config.description,
            experiment_type=self.__test_config.experiment_type,
        )
        for test in self.__test_config.tests:
            self.__client.reconnect()
            is_alive_cycle = Thread(target=self.__is_remote_alive, args=(test_completed_event,))
            is_alive_cycle.start()
            test(self.__executor, self.__client)
            test_completed_event.set()
            is_alive_cycle.join(10)
            test_completed_event.clear()
            self.__database.update_experiment_ended_at(experiment.experiment_id)
        self.logger.info("All tests completed successfully.")
        self.__client.close()

    def install_dependencies(self) -> None:
        from imgtests.exec.loaders import (  # noqa: PLC0415
            Chaosblade,
            Fio,
            FioPlot,
            Kirk,
            Perf,
            PhoronixTestSuite,
            StressNg,
        )

        self.logger.info("Installing dependencies. This may take a while.")
        for tool in (Chaosblade, Fio, FioPlot, Kirk, Perf, StressNg, PhoronixTestSuite):
            tool_instance: BaseTestUtil = tool(self.__client)
            try:
                tool_instance.install()
            except NotImplementedError:
                self.logger.exception(
                    "Failed to install dependencies for the '%s'.", tool_instance.name
                )
                continue
            tool_instance = tool(self.__client)
            self.logger.info(
                "Installed '%s' with version '%s'.", tool_instance.name, tool_instance.version()
            )
        self.logger.info("Dependencies installed successfully.")

    def __is_remote_alive(self, test_completed_event: Event) -> None:
        while not test_completed_event.wait(5.0):
            try:
                self.__client(["echo", "test"])
            except paramiko.ssh_exception.SSHException:
                break
        if not test_completed_event.is_set():
            self.logger.error("Remote node unavailable during test.")
            self.__client.close()
            self.__executor.shutdown(cancel_futures=True)
