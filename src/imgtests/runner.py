from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Event, Thread
from typing import TYPE_CHECKING, Any, Final, Literal

import paramiko
import paramiko.ssh_exception

from imgtests.constant import CONFIG_DIR, QEMU, REPORTS_DIR
from imgtests.database.database import ImgtestsDatabase
from imgtests.exec.exec import SSHClient, common_run_command, wait_remote
from imgtests.exec.observers.systemd_detect_virt import SystemdDetectVirt
from imgtests.exec.user_commands import Touch
from imgtests.planning import (
    AbstractRunnableManyTimesTest,
    AbstractRunnableTimeLimitedTest,
    BaseRunner,
    LoadPattern,
    PlanExecutor,
    TestKind,
)
from imgtests.snapshot import SnapshotManager
from imgtests.suites.system import (
    SystemLoadTimeTest,
    SystemSlowServicesTest,
)
from imgtests.types import Subsystem, TestsCounts, TestStatus

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from imgtests.database.models.experiment import ExperimentType
    from imgtests.exec.base_util import BaseTestUtil
    from imgtests.planning import LoadPattern


Runner = Literal["default", "profiled"]
Distro = Literal["all", "yocto", "opensuse"]

YOCTO_CONF: Final = (
    "SSH_YOCTO_ADDR",
    "SSH_YOCTO_USER",
    "SSH_YOCTO_PASS",
    "SSH_YOCTO_PORT",
)
SUSE_156_CONF: Final = (
    "SSH_SUSE_ADDR_156",
    "SSH_SUSE_USER",
    "SSH_SUSE_PASS",
    "SSH_SUSE_PORT_156",
)

logger = logging.getLogger()


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
        tests: Sequence[AbstractRunnableManyTimesTest | type[AbstractRunnableTimeLimitedTest]],
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
        # Use snapshot manager only when works with the remote and qemu
        if client is not None:
            systemd_detect_virt = SystemdDetectVirt(client)
            _, virt_type = systemd_detect_virt()
            self.__test_snapshots = (
                SnapshotManager("tests_runner", client)
                if virt_type is not None and QEMU in virt_type
                else None
            )
        else:
            self.__test_snapshots = None

    def run(self) -> None:
        snapshot_name = "vm-snapshot"
        if self.__test_snapshots and (
            self.__test_snapshots.snapshot_loaded
            or snapshot_name in self.__test_snapshots.get_snapshots_info().stdout
        ):
            self.__test_snapshots.switch_to_snapshot(snapshot_name)
        elif self.__test_config.install_dependencies:
            self.install_dependencies()
            if self.__test_snapshots:
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
            test_started_at = datetime.now(UTC)
            if isinstance(test_class, AbstractRunnableManyTimesTest):
                test_instance = test_class
            else:
                test_instance = test_class(timeout=self.__test_config.test_duration)
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
                until=datetime.now(UTC),
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


@dataclass(frozen=True)
class Durations:
    duration_sec: int = 120
    duration_load: int | None = None
    duration_stress: int | None = None
    duration_stability: int | None = None
    duration_scalability: int | None = None
    duration_volume: int | None = None
    duration_isolated: int | None = None
    duration_spike: int | None = None
    duration_diagnostic: int | None = None

    def duration_for(self, profile: TestKind) -> int:
        match profile:
            case TestKind.LOAD:
                duration = self.duration_load
            case TestKind.STRESS:
                duration = self.duration_stress
            case TestKind.STABILITY:
                duration = self.duration_stability
            case TestKind.SCALABILITY:
                duration = self.duration_scalability
            case TestKind.VOLUME:
                duration = self.duration_volume
            case TestKind.ISOLATED:
                duration = self.duration_isolated
            case TestKind.SPIKE:
                duration = self.duration_spike
            case TestKind.DIAGNOSTIC:
                duration = self.duration_diagnostic
            case _:
                return self.duration_sec
        return duration or self.duration_sec


class ProfiledPlanRunner(BaseRunner):
    def __init__(
        self,
        client: SSHClient | None,
        database: ImgtestsDatabase,
    ) -> None:
        self.executor = PlanExecutor(client=client, db=database)
        super().__init__("profiled_plan_runner", client, database)

    def run(  # noqa: PLR0913
        self,
        subsystems: frozenset[Subsystem] | None = None,
        results_dir: Path = REPORTS_DIR / "profiled",
        pattern: LoadPattern | None = None,
        run_matrix: bool = False,
        profile: TestKind = TestKind.LOAD,
        matrix_profiles: tuple[TestKind, ...] | None = None,
        durations: Durations | None = None,
    ) -> bool:
        if subsystems is None:
            subsystems = frozenset(Subsystem)
        elif not subsystems:
            msg = "No subsystems provided."
            raise ValueError(msg)
        if durations is None:
            durations = Durations()
        if matrix_profiles is None:
            matrix_profiles = tuple(TestKind)

        config_id = self.resolve_config_id(self._client, self._database)

        if run_matrix:
            return self._run_matrix(
                subsystems=subsystems,
                results_root=results_dir,
                pattern=pattern,
                matrix_profiles=matrix_profiles,
                config_id=config_id,
                durations=durations,
            )

        failures = self._run_one(
            profile=profile,
            duration_sec=durations.duration_sec,
            subsystems=subsystems,
            results_root=results_dir,
            pattern=pattern,
            config_id=config_id,
        )
        return failures > 0

    def _run_matrix(  # noqa: PLR0913
        self,
        *,
        subsystems: frozenset[Subsystem],
        results_root: Path,
        pattern: LoadPattern | None,
        matrix_profiles: tuple[TestKind, ...],
        config_id: int,
        durations: Durations,
    ) -> bool:
        if not matrix_profiles:
            msg = "No profiles provided."
            raise ValueError(msg)

        total_failures = 0

        for index, profile in enumerate(matrix_profiles):
            if index > 0 and isinstance(self._client, SSHClient):
                self._client.reconnect()

            duration_sec = durations.duration_for(profile)
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
        run_name = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        run_name = f"{run_name}_{profile.value}"
        if pattern is not None:
            run_name += f"_{pattern.value}"
        return run_name


def load_test_config(distro: str) -> dict[str, Any]:
    config_file = CONFIG_DIR / f"{distro}_config.json"
    if config_file.exists():
        try:
            with Path.open(config_file, "r") as f:
                config = json.load(f)
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to load config: %s, using default", e)
        else:
            logger.info("Loaded custom config for %s", distro)
            return config

    return {
        "suites": [
            "FILE_SUITE",
            "MEMORY_SUITE",
            "SYSCALLS_SUITE",
            "IPC_SUITE",
            "NETWORK_SUITE",
        ],
        "suite_durations": {},
        "selected_tests": {},
    }


def filter_tests_by_names(
    suite: TestsRunnerConfig,
    selected_test_names: list[str],
) -> Iterable[AbstractRunnableManyTimesTest | type[AbstractRunnableTimeLimitedTest]]:
    if not selected_test_names:
        return suite.tests

    original_tests = suite.tests
    filtered_tests: list[AbstractRunnableManyTimesTest | type[AbstractRunnableTimeLimitedTest]] = []

    for test in original_tests:
        test_name = get_test_name(test)

        if test_name in selected_test_names:
            filtered_tests.append(test)

    filtered_count = len(filtered_tests)

    if filtered_count == 0:
        logger.warning("No tests matched for %s, using all tests", suite.description)
        return original_tests

    return filtered_tests


def run_profiled(client: SSHClient, database: ImgtestsDatabase) -> None:
    client.reconnect()
    ProfiledPlanRunner(
        client=client,
        database=database,
    ).run()
    client.close()


def _get_clients(distro: str) -> tuple[SSHClient | None, SSHClient | None]:
    suse_client = None
    poky_client = None
    if distro in ("yocto", "all"):
        poky_client = wait_remote(*YOCTO_CONF) or sys.exit(1)
    if distro in ("opensuse", "all"):
        suse_client = wait_remote(*SUSE_156_CONF) or sys.exit(1)
        Touch(suse_client, use_sudo=True)(["/etc/cloud/cloud-init.disabled"])
    return suse_client, poky_client


def _run_single(distro: Distro, mode: Runner, config: dict[str, Any]) -> None:  # noqa: PLR0912, C901
    from imgtests.suites.map import (  # noqa: PLC0415
        ALL_SUBSYSTEMS_SUITE,
        ALL_SUITES,
    )

    logger.info("Running tests for %s", distro)
    logger.info("Using suites: %s", config.get("suites", []))
    suites_to_run = []
    for suite_name in config.get("suites", []):
        if suite_name in ALL_SUITES:
            suite = ALL_SUITES[suite_name]
            suite_durations = config.get("suite_durations", {})
            if suite_name in suite_durations:
                original_duration = suite.total_duration
                suite.total_duration = suite_durations[suite_name]
                logger.info(
                    "Overriding %s duration: %d -> %ds",
                    suite_name,
                    original_duration,
                    suite.total_duration,
                )

            selected_tests = config.get("selected_tests", {}).get(suite_name)
            if selected_tests and len(selected_tests) > 0:
                original_tests = suite.tests
                filtered_tests = []
                for test in original_tests:
                    test_name = get_test_name(test)
                    if test_name in selected_tests:
                        filtered_tests.append(test)

                if filtered_tests:
                    suite.tests = tuple(filtered_tests)
                    logger.info(
                        "Filtered %s: %d -> %d tests",
                        suite_name,
                        len(original_tests),
                        len(filtered_tests),
                    )
                    logger.info("Selected tests: %s", selected_tests)
                else:
                    logger.warning("No matching tests found for %s, using all tests", suite_name)

            suites_to_run.append(suite)
        else:
            logger.warning("Suite %s not found, skipping", suite_name)

    if not suites_to_run:
        logger.warning("No suites configured, running default ALL_SUBSYSTEMS_SUITE")
        suites_to_run = [ALL_SUBSYSTEMS_SUITE]

    suse_client, poky_client = _get_clients(distro)
    distros_to_test: list[SSHClient] = []
    if suse_client:
        distros_to_test.append(suse_client)
    if poky_client:
        distros_to_test.append(poky_client)

    database = ImgtestsDatabase()
    logger.info("Current testing mode is %s", mode)
    if mode == "default":
        for suite in suites_to_run:
            logger.info("Running suite %s", suite.description)
            for client in distros_to_test:
                client.reconnect()
                runner = TestsRunner(client, database, suite)
                runner.run()
                runner.close()
    if mode == "profiled":
        if poky_client:
            run_profiled(poky_client, database)
        if suse_client:
            run_profiled(suse_client, database)

    database.session.close_all()


def run_tests(
    distro: Distro = "all",
    mode: Runner = "default",
    test_runs_count: int = 1,
    config: dict[str, Any] | None = None,
) -> None:
    if config is None:
        config = load_test_config(distro)
    for i in range(test_runs_count):
        logger.info("Starting test run %d of %d", i + 1, test_runs_count)
        _run_single(distro, mode, config)
        logger.info("Completed test run %d of %d", i + 1, test_runs_count)


def get_test_name(
    test: AbstractRunnableManyTimesTest | type[AbstractRunnableTimeLimitedTest],
) -> str:
    if hasattr(test, "__name__"):
        return test.__name__
    if hasattr(test, "__class__"):
        return test.__class__.__name__
    return str(test)
