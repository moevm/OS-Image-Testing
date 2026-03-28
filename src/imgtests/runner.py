from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from threading import Event, Thread
from typing import TYPE_CHECKING, Any, ClassVar, NamedTuple
from zoneinfo import ZoneInfo

import paramiko
import paramiko.ssh_exception

from imgtests.constant import LIB_NAME
from imgtests.database.database import ExperimentType, ImgtestsDatabase
from imgtests.environment import env_var_to_type
from imgtests.exec.exec import SSHClient, common_run_command
from imgtests.exec.observers.journalctl import Journalctl
from imgtests.exec.observers.systemctl import Systemctl
from imgtests.sysrep import get_system_info
from imgtests.types import TestsCounts

if TYPE_CHECKING:
    from collections.abc import Iterable

    from imgtests.database.models.experiment import ExperimentBase
    from imgtests.exec.base_util import BaseTestUtil
    from imgtests.planning import LoadPattern, TestKind


class Subsystem(str, Enum):
    FILE = "file"
    IPC = "IPC"
    MEMORY = "memory"
    NETWORK = "network"
    SYSCALLS = "syscalls"
    SYSTEM = "system"


class TestStatus(Enum):
    PASSED = auto()
    FAILED = auto()
    SKIPPED = auto()
    BROKEN = auto()


class TestResult(NamedTuple):
    status: TestStatus
    metrics: Any = None
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


class BaseRunner:
    __slots__ = ()

    @staticmethod
    def resolve_config_id(
        client: SSHClient | None,
        database: ImgtestsDatabase,
        config_id: int | None = None,
    ) -> int:
        if config_id is not None:
            return int(config_id)

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


class TestsRunner(BaseRunner):
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
        experiment = self.start_experiment(
            client=self.__client,
            database=self.__database,
            description=self.__test_config.description,
            experiment_type=self.__test_config.experiment_type,
        )
        total_count = 0
        counts = {
            TestStatus.PASSED: 0,
            TestStatus.FAILED: 0,
            TestStatus.SKIPPED: 0,
            TestStatus.BROKEN: 0,
        }
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
                counts[result.status] += 1
                total_count += 1
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
            self.__database.update_experiment_tests_count(
                experiment.experiment_id,
                TestsCounts(
                    total_count=total_count,
                    broken_count=counts[TestStatus.BROKEN],
                    passed_count=counts[TestStatus.PASSED],
                    failed_count=counts[TestStatus.FAILED],
                    skip_count=counts[TestStatus.SKIPPED],
                ),
            )
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


class ProfiledPlanRunner(BaseRunner):
    __slots__ = ("client", "db", "executor")

    _SUBSYSTEM_ALIASES: ClassVar[dict[str, Subsystem]] = {
        "cpu": Subsystem.SYSTEM,
        "disk": Subsystem.FILE,
        "ipc": Subsystem.IPC,
    }

    def __init__(
        self,
        client: SSHClient,
        db: ImgtestsDatabase,
    ) -> None:
        from imgtests.planning.executor import PlanExecutor  # noqa: PLC0415

        self.client = client
        self.db = db
        self.executor = PlanExecutor(client=client, db=db)

    def run_from_env(self) -> int:
        subsystems = self._parse_subsystems(env_var_to_type("PLAN_SUBSYSTEMS", str, "all"))
        results_root = env_var_to_type("PLAN_RESULTS_DIR", Path, Path("results/profiled"))
        pattern = self._parse_pattern(env_var_to_type("PLAN_PATTERN", str, ""))
        config_id = self.resolve_config_id(self.client, self.db)

        if env_var_to_type("PLAN_RUN_MATRIX", bool, default=False):
            return self._run_matrix(
                subsystems=subsystems,
                results_root=results_root,
                pattern=pattern,
                config_id=config_id,
            )

        failures = self._run_one(
            profile=self._parse_profile(env_var_to_type("PLAN_PROFILE", str, "load")),
            duration_sec=env_var_to_type("PLAN_DURATION_SEC", int, 120),
            subsystems=subsystems,
            results_root=results_root,
            pattern=pattern,
            config_id=config_id,
        )
        return 1 if failures else 0

    def _run_matrix(
        self,
        *,
        subsystems: frozenset[Subsystem],
        results_root: Path,
        pattern: LoadPattern | None,
        config_id: int,
    ) -> int:
        total_failures = 0
        default_duration = env_var_to_type("PLAN_DURATION_SEC", int, 120)

        for index, profile in enumerate(
            self._parse_profiles(env_var_to_type("PLAN_MATRIX_PROFILES", str, "all"))
        ):
            if index > 0:
                self.client.reconnect()

            duration_sec = env_var_to_type(
                f"PLAN_DURATION_{profile.value.upper()}",
                int,
                default_duration,
            )
            total_failures += self._run_one(
                profile=profile,
                duration_sec=duration_sec,
                subsystems=subsystems,
                results_root=results_root,
                pattern=pattern,
                config_id=config_id,
            )

        return 1 if total_failures else 0

    def _run_one(  # noqa: PLR0913
        self,
        *,
        profile: TestKind,
        duration_sec: int,
        subsystems: frozenset[Subsystem],
        results_root: Path,
        pattern: LoadPattern | None,
        config_id: int,
    ) -> int:
        from imgtests.planning import PlanRequest, build_plan  # noqa: PLC0415

        execution = self.executor.execute(
            build_plan(
                PlanRequest(
                    duration_sec=duration_sec,
                    subsystems=subsystems,
                    test_kind=profile,
                    pattern=pattern,
                )
            ),
            results_dir=results_root / self._build_run_name(profile, pattern),
            experiment_description=f"Profiled plan: {profile.value}",
            config_id=config_id,
        )
        failures = sum(
            1 for stage in execution.stage_runs for task in stage.tasks if task.returncode != 0
        )

        logging.getLogger(__name__).info(
            "[PROFILED] DONE profile=%s pattern=%s duration=%ss failures=%d experiment_id=%s",
            profile.value,
            pattern.value if pattern else "auto",
            duration_sec,
            failures,
            execution.experiment_id,
        )
        logging.getLogger(__name__).info("[PROFILED] plan=%s", execution.plan_path)
        return failures

    @staticmethod
    def _build_run_name(profile: TestKind, pattern: LoadPattern | None) -> str:
        run_name = datetime.now(tz=ZoneInfo("UTC")).strftime("%Y%m%d_%H%M%S")
        run_name = f"{run_name}_{profile.value}"
        if pattern is not None:
            run_name += f"_{pattern.value}"
        return run_name

    @classmethod
    def _parse_subsystems(cls, raw: str) -> frozenset[Subsystem]:
        value = raw.strip().lower()
        if value == "all":
            return frozenset(Subsystem)

        subsystems: set[Subsystem] = set()
        for part in [item.strip().lower() for item in value.split(",") if item.strip()]:
            if part in cls._SUBSYSTEM_ALIASES:
                subsystems.add(cls._SUBSYSTEM_ALIASES[part])
                continue

            try:
                subsystems.add(Subsystem(part))
            except ValueError as exc:
                allowed = ", ".join(
                    sorted(
                        [subsystem.value for subsystem in Subsystem] + list(cls._SUBSYSTEM_ALIASES),
                    )
                )
                msg = f"Unknown subsystem '{part}'. Allowed: {allowed}"
                raise ValueError(msg) from exc

        if not subsystems:
            msg = "No subsystems provided."
            raise ValueError(msg)

        return frozenset(subsystems)

    @staticmethod
    def _parse_profile(raw: str) -> TestKind:
        from imgtests.planning import TestKind  # noqa: PLC0415

        try:
            return TestKind(raw.strip().lower())
        except ValueError as exc:
            allowed = ", ".join(item.value for item in TestKind)
            msg = f"Unknown profile '{raw}'. Allowed: {allowed}"
            raise ValueError(msg) from exc

    @classmethod
    def _parse_profiles(cls, raw: str) -> tuple[TestKind, ...]:
        from imgtests.planning import TestKind  # noqa: PLC0415

        value = raw.strip().lower()
        if value in {"", "all"}:
            return tuple(TestKind)

        profiles: list[TestKind] = []
        seen: set[TestKind] = set()
        for part in [item.strip() for item in value.split(",") if item.strip()]:
            profile = cls._parse_profile(part)
            if profile not in seen:
                profiles.append(profile)
                seen.add(profile)

        if not profiles:
            msg = "No profiles provided."
            raise ValueError(msg)

        return tuple(profiles)

    @staticmethod
    def _parse_pattern(raw: str) -> LoadPattern | None:
        from imgtests.planning import LoadPattern  # noqa: PLC0415

        value = raw.strip().lower()
        if value in {"", "auto"}:
            return None

        try:
            return LoadPattern(value)
        except ValueError as exc:
            allowed = ", ".join(item.value for item in LoadPattern)
            msg = f"Unknown pattern '{raw}'. Allowed: {allowed}"
            raise ValueError(msg) from exc
