import json
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Literal

from pydantic import Field
from pydantic_settings import BaseSettings

from imgtests.constant import CONFIG_DIR, LOG_PATH, REPORTS_DIR
from imgtests.database.database import ImgtestsDatabase
from imgtests.exec.exec import wait_remote
from imgtests.exec.user_commands import Touch
from imgtests.logger import set_handlers
from imgtests.reporting.html_report import ReportGenerator
from imgtests.runner import (
    AbstractRunnableManyTimesTest,
    AbstractRunnableTimeLimitedTest,
    ProfiledPlanRunner,
    TestsRunner,
    TestsRunnerConfig,
)
from imgtests.suites.map import (
    ALL_SUBSYSTEMS_SUITE,
    ALL_SUITES,
    get_test_name,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from imgtests.exec.base_util import SSHClient


Runners = Literal["default", "profiled"]
Distros = Literal["all", "yocto", "opensuse"]
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


def load_test_config(distro: Distros) -> dict[str, Any]:
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
    logger: logging.Logger,
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


def run_profiled(client: SSHClient, database: ImgtestsDatabase):
    client.reconnect()
    ProfiledPlanRunner(
        client=client,
        database=database,
    ).run_from_env()
    client.close()


def run_tests(distro: Distros, mode: Runners) -> None:  # noqa: PLR0912, PLR0915, C901
    logger.info("Running tests for %s", distro)
    config = load_test_config(distro)
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

    suse_client = None
    poky_client = None
    if distro in ("yocto", "all"):
        poky_client = wait_remote(*YOCTO_CONF) or sys.exit(1)
    if distro in ("opensuse", "all"):
        suse_client = wait_remote(*SUSE_156_CONF) or sys.exit(1)
        # disable cloud-init for the next boot for Suse according to documentation
        Touch(suse_client, use_sudo=True)(["/etc/cloud/cloud-init.disabled"])
    distros_to_test = []
    if suse_client:
        distros_to_test.append(suse_client)
    if poky_client:
        distros_to_test.append(poky_client)

    database = ImgtestsDatabase()

    # testing mode differentiation
    logger.info("Current tesing mode is %s", mode)
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

    report_generator = ReportGenerator(database)
    report_generator.generate_last_two_experiments_report(out_dir=REPORTS_DIR)

    database.session.close_all()


class TestsConfig(BaseSettings):
    distro: Distros = Field(validation_alias="TESTED_DISTRO", default="all")
    test_runs_count: int = Field(validation_alias="TEST_RUNS_COUNT", ge=1, default=1)
    runner: Runners = Field(validation_alias="TESTING_MODE", default="default")


def main() -> None:
    set_handlers(logger, LOG_PATH)
    test_config = TestsConfig()
    for i in range(test_config.test_runs_count):
        logger.info("Starting test run %d of %d", i + 1, test_config.test_runs_count)
        run_tests(test_config.distro, test_config.runner)
        logger.info("Completed test run %d of %d", i + 1, test_config.test_runs_count)


if __name__ == "__main__":
    main()
