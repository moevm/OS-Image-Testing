import logging
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from enum import Enum
from threading import Event, Thread
from typing import TYPE_CHECKING, Any, NamedTuple
from zoneinfo import ZoneInfo

import paramiko
import paramiko.ssh_exception

from imgtests.constant import LIB_NAME
from imgtests.database.database import ImgtestsDatabase
from imgtests.exec.exec import common_run_command
from imgtests.exec.observers.journalctl import Journalctl
from imgtests.exec.observers.systemctl import Systemctl
from imgtests.sysrep import get_system_info

if TYPE_CHECKING:
    from collections.abc import Iterable

    from imgtests.database.database import ExperimentType
    from imgtests.exec.base_util import BaseTestUtil
    from imgtests.exec.exec import SSHClient


class Subsystem(str, Enum):
    FILE = "file"
    IPC = "IPC"
    MEMORY = "memory"
    NETWORK = "network"
    SYSCALLS = "syscalls"
    SYSTEM = "system"


class TestResult(NamedTuple):
    metrics: Any
    command: str = ""
    started_at: datetime = datetime.now(tz=ZoneInfo("UTC"))
    ended_at: datetime = datetime.now(tz=ZoneInfo("UTC"))


class DefaultCleanupMixin:
    def cleanup(self, client: SSHClient | None, logger: logging.Logger) -> None:
        for path in ("/tmp/*", "/var/tmp/*"):  # noqa: S108
            result = common_run_command(["sudo", "rm", "-rf", path], client)
            if result.returncode:
                logger.warning("Failed to cleanup folder '%s'.", path)
            else:
                logger.info("Cleaned up folder '%s'.", path)


class AbstractRunnableManyTimesTest(ABC, DefaultCleanupMixin):
    __slots__ = ("description", "iterations", "logger", "subsystems")

    def __init__(
        self,
        description: str,
        subsystems: frozenset[Subsystem],
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

    def __call__(
        self, executor: ThreadPoolExecutor, client: SSHClient | None = None
    ) -> Iterable[TestResult]:
        self.logger.info("Starting '%s' test '%d' times.", self.description, self.iterations)
        yield from self._run(executor, client, self.iterations)
        self.logger.info("'%s' test finished.", self.description)

    @abstractmethod
    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        iterations: int,
    ) -> Iterable[TestResult]: ...


class AbstractRunnableTimeLimitedTest(ABC, DefaultCleanupMixin):
    __slots__ = ("description", "logger", "subsystems", "timeout")

    def __init__(
        self,
        description: str,
        subsystems: frozenset[Subsystem],
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

    def __call__(
        self, executor: ThreadPoolExecutor, client: SSHClient | None = None
    ) -> Iterable[TestResult]:
        self.logger.info("Starting '%s' test with '%d' timeout.", self.description, self.timeout)
        yield from self._run(executor, client, self.timeout)
        self.logger.info("'%s' test finished.", self.description)

    @abstractmethod
    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]: ...


# Time to run, subsystems, stages (plan, risk analysis, run, cleanup, results, etc), etc
class TestsRunnerConfig(NamedTuple):
    description: str
    tests: Iterable[AbstractRunnableManyTimesTest | AbstractRunnableTimeLimitedTest]
    experiment_type: ExperimentType
    install_dependencies: bool = False


class TestsRunner:
    __slots__ = ("__client", "__database", "__executor", "__test_config", "logger")

    def __init__(self, client: SSHClient | None, test_config: TestsRunnerConfig) -> None:
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
            if self.__client is not None:
                self.__client.reconnect()
            is_alive_cycle = Thread(target=self.__is_remote_alive, args=(test_completed_event,))
            is_alive_cycle.start()
            test_started_at = datetime.now(tz=ZoneInfo("UTC"))
            for result in test(self.__executor, self.__client):
                self.__database.insert_loader(
                    experiment_id=experiment.experiment_id,
                    # TODO: fill descriptions and adds into TestResult class
                    description="",
                    result=result.metrics,
                    command=result.command,
                    started_at=result.started_at,
                    ended_at=result.ended_at,
                )
            self._collect_system_errors(
                experiment_id=experiment.experiment_id,
                since=test_started_at,
                until=datetime.now(tz=ZoneInfo("UTC")),
            )
            test.cleanup(self.__client, self.logger)
            test_completed_event.set()
            is_alive_cycle.join(10)
            test_completed_event.clear()
            self.__database.update_experiment_ended_at(experiment.experiment_id)
        self.logger.info("All tests completed successfully.")
        if self.__client is not None:
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
        from imgtests.exec.observers import NodeExporter, Sar, Time  # noqa: PLC0415

        self.logger.info("Installing dependencies. This may take a while.")
        for tool in (
            Chaosblade,
            Fio,
            FioPlot,
            Kirk,
            Perf,
            StressNg,
            PhoronixTestSuite,
            Time,
            NodeExporter,
            Sar,
        ):
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
                common_run_command(["echo", "test"], self.__client)
            except paramiko.ssh_exception.SSHException:
                break
        if not test_completed_event.is_set():
            self.logger.error("Remote node unavailable during test.")
            if self.__client is not None:
                self.__client.close()
            self.__executor.shutdown(cancel_futures=True)

    def _collect_system_errors(self, experiment_id: int, since: datetime, until: datetime) -> None:
        systemctl = Systemctl(self.__client)
        journalctl = Journalctl(self.__client, use_sudo=True)

        # failed services
        fs_r, fs_m = systemctl.get_failed_services()
        self.logger.info("Failed services: %s", fs_m)
        self.__database.insert_observer(
            experiment_id=experiment_id,
            command=" ".join(fs_r.cmd),
            description="Failed systemd services.",
            result=systemctl.metrics_to_json(fs_m),
        )

        # OOM
        oom_r = journalctl.oom_records(
            since=since.strftime(journalctl.DATE_FORMAT),
            until=until.strftime(journalctl.DATE_FORMAT),
        )
        oom_m = journalctl.calc_records_cnt(oom_r.stdout)
        self.logger.info("OOM records %d", oom_m)
        self.__database.insert_observer(
            experiment_id=experiment_id,
            command=" ".join(oom_r.cmd),
            description="OOM records.",
            started_at=since,
            ended_at=until,
            result=journalctl.metrics_to_json(oom_m),
        )

        # systemd errors
        sstmd_err_r = journalctl.systemd_only_records(
            since=since.strftime(journalctl.DATE_FORMAT),
            until=until.strftime(journalctl.DATE_FORMAT),
            priority="err",
        )
        sstmd_err_m = journalctl.calc_records_cnt(sstmd_err_r.stdout)
        self.logger.info(
            "systemd errors records %d",
            sstmd_err_m,
        )
        self.__database.insert_observer(
            experiment_id=experiment_id,
            command=" ".join(sstmd_err_r.cmd),
            description="Systemd errors records",
            started_at=since,
            ended_at=until,
            result=journalctl.metrics_to_json(sstmd_err_m),
        )
