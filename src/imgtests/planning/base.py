import logging
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from imgtests.constant import LIB_NAME
from imgtests.exec.exec import SSHClient, Verbosity, common_run_command
from imgtests.exec.observers.journalctl import Journalctl
from imgtests.exec.observers.systemctl import Systemctl
from imgtests.sysrep import get_system_info
from imgtests.types import MetricSample, Subsystem

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import datetime

    from imgtests.database.database import ImgtestsDatabase
    from imgtests.database.models.experiment import ExperimentBase, ExperimentType
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


class BaseRunner:
    def __init__(self, name: str, client: SSHClient | None, database: ImgtestsDatabase) -> None:
        self._executor = ThreadPoolExecutor()
        self._client = client
        self._database = database
        self._logger = logging.getLogger(f"{LIB_NAME}.{name}")

    @staticmethod
    def resolve_config_id(
        client: SSHClient | None,
        database: ImgtestsDatabase,
        config_id: int | None = None,
    ) -> int:
        if config_id is not None:
            return config_id

        result = get_system_info(client)
        configuration_record = database.insert_from_system_info(result)
        return int(configuration_record.config_id)

    @classmethod
    def start_experiment(  # noqa: PLR0913
        cls,
        *,
        client: SSHClient | None,
        database: ImgtestsDatabase,
        description: str,
        experiment_type: ExperimentType,
        config_id: int | None = None,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
    ) -> ExperimentBase:
        return database.insert_experiment(
            config_id=cls.resolve_config_id(client, database, config_id),
            description=description,
            experiment_type=experiment_type,
            started_at=started_at,
            ended_at=ended_at,
        )

    def _collect_system_errors(
        self,
        experiment_id: int,
        since: datetime,
        until: datetime,
    ) -> list[MetricSample]:
        systemctl = Systemctl(self._client)
        journalctl = Journalctl(self._client, use_sudo=True)
        collected_metrics: list[MetricSample] = []

        fs_r, fs_m = systemctl.get_failed_services()
        self._logger.info("Failed services: %s", fs_m)
        collected_metrics.append(
            MetricSample(
                stage_name="system-errors",
                subsystem="system",
                metric_name="failed systemd services",
                value=float(len(fs_m)),
                label="failed systemd services",
            ),
        )

        self._database.insert_util_run_result(
            experiment_id=experiment_id,
            util_type="observer",
            command=" ".join(fs_r.cmd),
            result=systemctl.metrics_to_json(fs_m),
            description="failed systemd services",
        )

        # OOM
        oom_r = journalctl.oom_records(
            since=since.strftime(journalctl.DATE_FORMAT),
            until=until.strftime(journalctl.DATE_FORMAT),
            verbosity=Verbosity(0),
        )
        oom_m = journalctl.calc_records_cnt(oom_r.stdout)
        self._logger.info("OOM records %d", oom_m)
        collected_metrics.append(
            MetricSample(
                stage_name="system-errors",
                subsystem="system",
                metric_name="OOM records",
                value=float(oom_m),
                label="OOM records",
            ),
        )
        self._database.insert_util_run_result(
            experiment_id=experiment_id,
            util_type="observer",
            command=" ".join(oom_r.cmd),
            result=journalctl.metrics_to_json(oom_m),
            description="OOM records",
            started_at=since,
            ended_at=until,
        )

        # systemd errors
        sstmd_err_r = journalctl.systemd_only_records(
            since=since.strftime(journalctl.DATE_FORMAT),
            until=until.strftime(journalctl.DATE_FORMAT),
            priority="err",
            verbosity=Verbosity(0),
        )
        sstmd_err_m = journalctl.calc_records_cnt(sstmd_err_r.stdout)
        self._logger.info(
            "systemd errors records %d",
            sstmd_err_m,
        )
        collected_metrics.append(
            MetricSample(
                stage_name="system-errors",
                subsystem="system",
                metric_name="systemd errors records",
                value=float(sstmd_err_m),
                label="systemd errors records",
            ),
        )
        self._database.insert_util_run_result(
            experiment_id=experiment_id,
            util_type="observer",
            command=" ".join(sstmd_err_r.cmd),
            description="systemd errors records",
            started_at=since,
            ended_at=until,
            result=journalctl.metrics_to_json(sstmd_err_m),
        )

        return collected_metrics

    def close(self) -> None:
        self._executor.shutdown(wait=False)


def calc_subtest_timeout(timeout: int, tests_cnt: int, min_subtest_timeout: int = 1) -> int:
    subtest_timeout = timeout // tests_cnt
    if min_subtest_timeout < 0:
        err_msg = "min_subtest_timeout must be positive"
        raise ValueError(err_msg)
    if subtest_timeout < min_subtest_timeout:
        err_msg = (
            f"Insufficient timeout provided. Needs at least '{min_subtest_timeout * tests_cnt}'."
        )
        raise ValueError(err_msg)
    return subtest_timeout
