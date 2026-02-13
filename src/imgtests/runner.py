import logging
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Thread
from typing import TYPE_CHECKING, NamedTuple

import paramiko
import paramiko.ssh_exception

from imgtests.database.database import ImgtestsDatabase

if TYPE_CHECKING:
    from imgtests.exec.base_util import BaseTestUtil
from imgtests.exec.exec import SSHClient
from imgtests.sysrep import get_system_info


# Time to run, subsystems, stages (install, ..., run, cleanup, results, etc), etc
class TestConfig(NamedTuple):
    tests: Iterable[Callable[[ThreadPoolExecutor, SSHClient], None]]


class TestRunner:
    __slots__ = ("__client", "__database", "__executor", "__test_config", "logger")

    def __init__(self, client: SSHClient, test_config: TestConfig, logger: logging.Logger) -> None:
        self.__executor = ThreadPoolExecutor()
        self.__client = client
        self.__database = ImgtestsDatabase()
        self.__test_config = test_config
        self.logger = logger

    def run(self) -> None:
        test_completed_event = Event()
        result = get_system_info(self.__client)
        self.__database.insert_from_system_info(result)
        for test in self.__test_config.tests:
            self.__client.reconnect()
            is_alive_cycle = Thread(target=self.__is_remote_alive, args=(test_completed_event,))
            is_alive_cycle.start()
            self.logger.info("Starting '%s' tests.", test.__name__)
            test(self.__executor, self.__client)
            self.logger.info("'%s' tests finished.", test.__name__)
            test_completed_event.set()
            is_alive_cycle.join(10)
            test_completed_event.clear()
        self.logger.info("All tests completed successfully.")
        self.__client.close()

    def install_dependencies(self, client: SSHClient | None) -> None:
        from imgtests.exec.loaders import (  # noqa: PLC0415
            Chaosblade,
            Fio,
            FioPlot,
            Kirk,
            Perf,
            PhoronixTestSuite,
            StressNg,
        )

        for tool in (Chaosblade, Fio, FioPlot, Kirk, Perf, StressNg, PhoronixTestSuite):
            tool_instance: BaseTestUtil = tool(client)
            try:
                tool_instance.install()
            except NotImplementedError:
                self.logger.exception(
                    "Failed to install dependencies for the '%s'.", tool_instance.name
                )
                continue
            tool_instance = tool(client)
            self.logger.info(
                "Installed '%s' with version '%s'.", tool_instance.name, tool_instance.version()
            )

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
