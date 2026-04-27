import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from imgtests.constant import LIB_NAME
from imgtests.exec.exec import SSHClient, common_run_command

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.types import Subsystem, TestResult


class DefaultCleanupMixin:
    def cleanup(self, client: SSHClient | None, logger: logging.Logger) -> None:
        for path in ("/tmp/*", "/var/tmp/*"):  # noqa: S108
            result = common_run_command(["sudo", "rm", "-rf", path], client)
            if result.returncode:
                logger.warning("Failed to cleanup folder '%s'.", path)
            else:
                logger.info("Cleaned up folder '%s'.", path)
        self.__clean_pages_cache(client, logger)

    def __clean_pages_cache(self, client: SSHClient | None, logger: logging.Logger) -> None:
        commands = [["sudo", "sync"], ["sudo", "sh", "-c", "'echo 3 > /proc/sys/vm/drop_caches'"]]
        for command in commands:
            result = common_run_command(command, client)
            if result.returncode:
                logger.warning("Cache cleanup failed.")


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
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None = None,
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
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None = None,
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
