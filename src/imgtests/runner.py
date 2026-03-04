import logging
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Thread
from typing import TYPE_CHECKING, Any, Literal, NamedTuple

import paramiko
import paramiko.ssh_exception

from imgtests.constant import LIB_NAME
from imgtests.database.database import ImgtestsDatabase
from imgtests.exec.observers.systemctl import Systemctl
from imgtests.sysrep import get_system_info

if TYPE_CHECKING:
    from collections.abc import Iterable

    from imgtests.database.database import ExperimentType
    from imgtests.exec.base_util import BaseTestUtil
    from imgtests.exec.exec import SSHClient

Subsystem = Literal["file", "syscalls", "IPC", "network", "memory", "system"]


class AbstractRunnableManyTimesTest(ABC):
    __slots__ = ("description", "iterations", "logger", "subsystems")

    def __init__(
        self,
        description: str,
        subsystems: set[Subsystem],
        iterations: int = 1,
    ) -> None:
        """Construct a AbstractRunnableManyTimesTest instance.

        Initializes the runnable test with description, target subsystems,
        execution logic, and repetition parameters.

        Args:
            description: Test description.
            subsystems: Covered subsystems with the test.
            iterations: Count of test iterations to run. Defaults to 1.

        Raises:
            ValueError: If iterations is less than 1.
        """
        if iterations < 1:
            err_msg = "Iterations must be at least 1."
            raise ValueError(err_msg)

        self.description = description
        self.subsystems = subsystems
        self.iterations = iterations
        self.logger = logging.getLogger(f"{LIB_NAME}.runnable_test")

    def __call__(self, executor: ThreadPoolExecutor, client: SSHClient | None = None) -> Any:
        self.logger.info("Starting '%s' test '%d' times.", self.description, self.iterations)
        self._run(executor, client, self.iterations)
        self.logger.info("'%s' test finished.", self.description)

    @abstractmethod
    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        iterations: int,
    ) -> None: ...


class AbstractRunnableTimeLimitedTest(ABC):
    __slots__ = ("description", "logger", "subsystems", "timeout")

    def __init__(
        self,
        description: str,
        subsystems: set[Subsystem],
        timeout: int,
    ) -> None:
        """Construct a AbstractRunnableTimeLimitedTest instance.

        Initializes the runnable test with description, target subsystems,
        execution logic, and time to run.

        Args:
            description: Test description.
            subsystems: Covered subsystems with the test.
            timeout: Test time to run if needed.

        Raises:
            ValueError: If timeout is negative.
        """
        if timeout < 0:
            err_msg = "Timeout must be positive."
            raise ValueError(err_msg)

        self.description = description
        self.subsystems = subsystems
        self.timeout = timeout
        self.logger = logging.getLogger(f"{LIB_NAME}.runnable_test")

    def __call__(self, executor: ThreadPoolExecutor, client: SSHClient | None = None) -> Any:
        self.logger.info("Starting '%s' test with '%d' timeout.", self.description, self.timeout)
        self._run(executor, client, self.timeout)
        self.logger.info("'%s' test finished.", self.description)

    @abstractmethod
    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> None: ...


# Time to run, subsystems, stages (plan, risk analysis, run, cleanup, results, etc), etc
class TestsRunnerConfig(NamedTuple):
    description: str
    tests: Iterable[AbstractRunnableManyTimesTest | AbstractRunnableTimeLimitedTest]
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
        systemctl = Systemctl(self.__client)
        self.logger.info("Failed services: %s", systemctl.get_failed_services())
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
        from imgtests.exec.observers.time import Time  # noqa: PLC0415

        self.logger.info("Installing dependencies. This may take a while.")
        for tool in (Chaosblade, Fio, FioPlot, Kirk, Perf, StressNg, PhoronixTestSuite, Time):
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
