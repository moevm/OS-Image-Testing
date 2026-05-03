from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from threading import Event, Thread
from typing import TYPE_CHECKING, ClassVar
from zoneinfo import ZoneInfo

import paramiko
import paramiko.ssh_exception
from pydantic import Field
from pydantic_settings import BaseSettings

from imgtests.constant import LIB_NAME
from imgtests.exec.exec import SSHClient, Verbosity, common_run_command
from imgtests.exec.observers.journalctl import Journalctl
from imgtests.exec.observers.systemctl import Systemctl
from imgtests.planning import (
    AbstractRunnableManyTimesTest,
    AbstractRunnableTimeLimitedTest,
    TestKind,
)
from imgtests.snapshot import SnapshotManager
from imgtests.suites.system import (
    SystemLoadTimeTest,
    SystemSlowServicesTest,
)
from imgtests.sysrep import get_system_info
from imgtests.types import Subsystem, TestsCounts, TestStatus

if TYPE_CHECKING:
    from collections.abc import Iterable

    from imgtests.database.database import ImgtestsDatabase
    from imgtests.database.models.experiment import ExperimentBase, ExperimentType
    from imgtests.exec.base_util import BaseTestUtil
    from imgtests.planning import LoadPattern

TIMEOUT_RETURN_CODE: int = 124


# Subsystems, stages (plan, risk analysis, run, cleanup, results, etc), etc
class TestsRunnerConfig:
    __slots__ = (
        "description",
        "experiment_type",
        "install_dependencies",
        "test_duration",
        "tests",
        "total_duration",
    )

    def __init__(
        self,
        description: str,
        tests: Iterable[AbstractRunnableManyTimesTest | type[AbstractRunnableTimeLimitedTest]],
        experiment_type: ExperimentType,
        duration: int,
        install_dependencies: bool = False,
    ) -> None:
        self.description = description
        self.tests = tests
        self.experiment_type: ExperimentType = experiment_type
        self.total_duration = duration
        self.install_dependencies = install_dependencies
        time_limited_tests_cnt = sum(
            1 for test in self.tests if not isinstance(test, AbstractRunnableManyTimesTest)
        )
        if time_limited_tests_cnt > self.total_duration:
            err_msg = (
                f"Each test cannot be run for less 1 second. "
                f"{self.total_duration} seconds available, {time_limited_tests_cnt} tests to run. "
                "Available time is not enough."
            )
            raise ValueError(err_msg)
        if time_limited_tests_cnt > 0:
            self.test_duration = self.total_duration // time_limited_tests_cnt
        else:
            self.test_duration = 0


class ProfiledPlanRunnerSettings(BaseSettings):
    subsystems: str = Field(default="all", validation_alias="PLAN_SUBSYSTEMS")
    results_dir: Path = Field(
        default=Path("results/profiled"),
        validation_alias="PLAN_RESULTS_DIR",
    )
    pattern: str = Field(default="", validation_alias="PLAN_PATTERN")
    run_matrix: bool = Field(default=False, validation_alias="PLAN_RUN_MATRIX")
    profile: str = Field(default="load", validation_alias="PLAN_PROFILE")
    duration_sec: int = Field(default=120, validation_alias="PLAN_DURATION_SEC")
    matrix_profiles: str = Field(default="all", validation_alias="PLAN_MATRIX_PROFILES")
    duration_load: int | None = Field(default=None, validation_alias="PLAN_DURATION_LOAD")
    duration_stress: int | None = Field(default=None, validation_alias="PLAN_DURATION_STRESS")
    duration_stability: int | None = Field(default=None, validation_alias="PLAN_DURATION_STABILITY")
    duration_scalability: int | None = Field(
        default=None,
        validation_alias="PLAN_DURATION_SCALABILITY",
    )
    duration_volume: int | None = Field(default=None, validation_alias="PLAN_DURATION_VOLUME")
    duration_isolated: int | None = Field(default=None, validation_alias="PLAN_DURATION_ISOLATED")
    duration_spike: int | None = Field(default=None, validation_alias="PLAN_DURATION_SPIKE")
    duration_diagnostic: int | None = Field(
        default=None,
        validation_alias="PLAN_DURATION_DIAGNOSTIC",
    )

    def duration_for(self, profile: TestKind) -> int:
        durations = {
            "load": self.duration_load,
            "stress": self.duration_stress,
            "stability": self.duration_stability,
            "scalability": self.duration_scalability,
            "volume": self.duration_volume,
            "isolated": self.duration_isolated,
            "spike": self.duration_spike,
            "diagnostic": self.duration_diagnostic,
        }
        duration = durations[profile.value]
        return self.duration_sec if duration is None else duration


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

    def close(self) -> None:
        self._executor.shutdown(wait=False)


class TestsRunner(BaseRunner):
    def __init__(
        self,
        client: SSHClient | None,
        database: ImgtestsDatabase,
        test_config: TestsRunnerConfig,
    ) -> None:
        super().__init__("tests_runner", client, database)
        self.__test_config = test_config
        self.__tests_cnt = 0
        self.__tests_statuses = {
            TestStatus.PASSED: 0,
            TestStatus.FAILED: 0,
            TestStatus.SKIPPED: 0,
            TestStatus.BROKEN: 0,
        }
        self.__test_snapshots = SnapshotManager("tests_runner", client)

    def run(self) -> None:
        result = self.__test_snapshots.get_snapshots_info()
        snapshot_name = "vm-snapshot"
        if snapshot_name in result.stdout:
            self.__test_snapshots.switch_to_snapshot(snapshot_name)
        elif self.__test_config.install_dependencies:
            self.install_dependencies()
            self.__test_snapshots.create_snapshot(snapshot_name)

        experiment = self.start_experiment(
            client=self._client,
            database=self._database,
            description=self.__test_config.description,
            experiment_type=self.__test_config.experiment_type,
        )
        self.handle_tests(
            (SystemLoadTimeTest(), SystemSlowServicesTest()),
            experiment.experiment_id,
        )
        self.handle_tests(self.__test_config.tests, experiment.experiment_id)
        self._logger.info("All tests completed successfully.")
        if self._client is not None:
            self._client.close()

    def handle_tests(
        self,
        tests: Iterable[AbstractRunnableManyTimesTest | type[AbstractRunnableTimeLimitedTest]],
        experiment_id: int,
    ) -> None:
        test_completed_event = Event()
        for test_class in tests:
            if self._client is not None:
                self._client.reconnect()
            is_alive_cycle = Thread(target=self.__is_remote_alive, args=(test_completed_event,))
            is_alive_cycle.start()
            test_started_at = datetime.now(tz=ZoneInfo("UTC"))
            if isinstance(test_class, AbstractRunnableManyTimesTest):
                test_instance = test_class
            else:
                test_instance = test_class(self.__test_config.test_duration)
            for result in test_instance(self._executor, self._client):
                self._database.insert_util_run_result(
                    experiment_id=experiment_id,
                    # TODO: fill util_type with the correct value
                    util_type="loader",
                    # TODO: fill descriptions and adds into TestResult class
                    description="",
                    result=result.metrics,
                    command=result.command,
                    started_at=result.started_at,
                    ended_at=result.ended_at,
                )
                self.__tests_statuses[result.status] += 1
                self.__tests_cnt += 1
            self._collect_system_errors(
                experiment_id=experiment_id,
                since=test_started_at,
                until=datetime.now(tz=ZoneInfo("UTC")),
            )
            test_instance.cleanup(self._client, self._logger)
            test_completed_event.set()
            is_alive_cycle.join(10)
            test_completed_event.clear()
            self._database.update_experiment_ended_at(experiment_id)
            self._database.update_experiment_tests_count(
                experiment_id,
                TestsCounts(
                    total_count=self.__tests_cnt,
                    broken_count=self.__tests_statuses[TestStatus.BROKEN],
                    passed_count=self.__tests_statuses[TestStatus.PASSED],
                    failed_count=self.__tests_statuses[TestStatus.FAILED],
                    skip_count=self.__tests_statuses[TestStatus.SKIPPED],
                ),
            )

    def install_dependencies(self) -> None:
        from imgtests.exec.loaders import (  # noqa: PLC0415
            Chaosblade,
            Fio,
            Iperf3,
            Kirk,
            Perf,
            PhoronixTestSuite,
            StressNg,
        )
        from imgtests.exec.observers import Lshw, NodeExporter, Sar  # noqa: PLC0415
        from imgtests.exec.user_commands import Time  # noqa: PLC0415

        self._logger.info("Installing dependencies. This may take a while.")
        for tool in (
            Chaosblade,
            Fio,
            Kirk,
            Perf,
            StressNg,
            PhoronixTestSuite,
            Time,
            NodeExporter,
            Sar,
            Lshw,
            Iperf3,
        ):
            tool_instance: BaseTestUtil = tool(self._client)
            try:
                result = tool_instance.install()
            except NotImplementedError:
                self._logger.exception(
                    "Failed to install dependencies for the '%s'.",
                    tool_instance.name,
                )
                continue
            if result.returncode:
                self._logger.error(
                    "Failed to install dependencies for the '%s'.",
                    tool_instance.name,
                )
            else:
                tool_instance = tool(self._client)
                self._logger.info(
                    "Installed '%s' with version '%s'.",
                    tool_instance.name,
                    tool_instance.version(),
                )
        self._logger.info("Dependencies installed successfully.")

    def __is_remote_alive(self, test_completed_event: Event) -> None:
        while not test_completed_event.wait(5.0):
            try:
                common_run_command(["echo", "test"], self._client)
            except paramiko.ssh_exception.SSHException:
                break
        if not test_completed_event.is_set():
            self._logger.error("Remote node unavailable during test.")
            if self._client is not None:
                self._client.close()
            self._executor.shutdown(cancel_futures=True)

    def _collect_system_errors(self, experiment_id: int, since: datetime, until: datetime) -> None:
        systemctl = Systemctl(self._client)
        journalctl = Journalctl(self._client, use_sudo=True)

        # failed services
        fs_r, fs_m = systemctl.get_failed_services()
        self._logger.info("Failed services: %s", fs_m)
        self._database.insert_util_run_result(
            experiment_id=experiment_id,
            util_type="observer",
            command=" ".join(fs_r.cmd),
            description="Failed systemd services.",
            result=systemctl.metrics_to_json(fs_m),
        )

        # OOM
        oom_r = journalctl.oom_records(
            since=since.strftime(journalctl.DATE_FORMAT),
            until=until.strftime(journalctl.DATE_FORMAT),
            verbosity=Verbosity(0),
        )
        oom_m = journalctl.calc_records_cnt(oom_r.stdout)
        self._logger.info("OOM records %d", oom_m)
        self._database.insert_util_run_result(
            experiment_id=experiment_id,
            util_type="observer",
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
            verbosity=Verbosity(0),
        )
        sstmd_err_m = journalctl.calc_records_cnt(sstmd_err_r.stdout)
        self._logger.info(
            "systemd errors records %d",
            sstmd_err_m,
        )
        self._database.insert_util_run_result(
            experiment_id=experiment_id,
            util_type="observer",
            command=" ".join(sstmd_err_r.cmd),
            description="Systemd errors records",
            started_at=since,
            ended_at=until,
            result=journalctl.metrics_to_json(sstmd_err_m),
        )


class ProfiledPlanRunner(BaseRunner):
    _SUBSYSTEM_ALIASES: ClassVar[dict[str, Subsystem]] = {
        "cpu": Subsystem.SYSTEM,
        "disk": Subsystem.FILE,
        "ipc": Subsystem.IPC,
    }

    def __init__(
        self,
        client: SSHClient | None,
        database: ImgtestsDatabase,
    ) -> None:
        from imgtests.planning.executor import PlanExecutor  # noqa: PLC0415

        self.executor = PlanExecutor(client=client, db=database)
        super().__init__("profiled_plan_runner", client, database)

    def run_from_env(self) -> bool:
        settings = ProfiledPlanRunnerSettings()
        subsystems = self._parse_subsystems(settings.subsystems)
        results_root = settings.results_dir
        pattern = self._parse_pattern(settings.pattern)
        config_id = self.resolve_config_id(self._client, self._database)

        if settings.run_matrix:
            return self._run_matrix(
                subsystems=subsystems,
                results_root=results_root,
                pattern=pattern,
                config_id=config_id,
                settings=settings,
            )

        failures = self._run_one(
            profile=self._parse_profile(settings.profile),
            duration_sec=settings.duration_sec,
            subsystems=subsystems,
            results_root=results_root,
            pattern=pattern,
            config_id=config_id,
        )
        return failures > 0

    def _run_matrix(
        self,
        *,
        subsystems: frozenset[Subsystem],
        results_root: Path,
        pattern: LoadPattern | None,
        config_id: int,
        settings: ProfiledPlanRunnerSettings,
    ) -> bool:
        total_failures = 0

        for index, profile in enumerate(self._parse_profiles(settings.matrix_profiles)):
            if index > 0 and isinstance(self._client, SSHClient):
                self._client.reconnect()

            duration_sec = settings.duration_for(profile)
            total_failures += self._run_one(
                profile=profile,
                duration_sec=duration_sec,
                subsystems=subsystems,
                results_root=results_root,
                pattern=pattern,
                config_id=config_id,
            )

        return total_failures > 0

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
                ),
            ),
            results_dir=results_root / self._build_run_name(profile, pattern),
            experiment_description=f"Profiled plan: {profile.value}",
            config_id=config_id,
        )
        failures = sum(
            1 for stage in execution.stage_runs for task in stage.tasks if task.returncode != 0
        )

        self._logger.info(
            "[PROFILED] DONE profile=%s pattern=%s duration=%ss failures=%d experiment_id=%s",
            profile.value,
            pattern.value if pattern else "auto",
            duration_sec,
            failures,
            execution.experiment_id,
        )
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
                    ),
                )
                msg = f"Unknown subsystem '{part}'. Allowed: {allowed}"
                raise ValueError(msg) from exc

        if not subsystems:
            msg = "No subsystems provided."
            raise ValueError(msg)

        return frozenset(subsystems)

    @staticmethod
    def _parse_profile(raw: str) -> TestKind:
        try:
            return TestKind(raw.strip().lower())
        except ValueError as exc:
            allowed = ", ".join(item.value for item in TestKind)
            msg = f"Unknown profile '{raw}'. Allowed: {allowed}"
            raise ValueError(msg) from exc

    @classmethod
    def _parse_profiles(cls, raw: str) -> tuple[TestKind, ...]:
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
