import json
import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from image.endurance.memory import StressNgEnduranceMemoryTest
from image.endurance.syscalls import (
    LTPSyscallsIPCTest,
    LTPSyscallsTest,
    StressNgEnduranceSyscallsTest,
)
from image.performance.cpu import ChaosbladeCPUTest, StressNgPerformanceCpuTest
from image.performance.fio_disks import (
    FioDisksDMDelay,
    FioDisksDMDust,
    FioDisksNightly,
    FioDisksParallelLoadTest,
    FioDisksScalingTest,
    FioDisksVariationTest,
)
from image.performance.ipc import SchedPerformanceTest
from image.performance.memory import SarWithStressNGTest, StressNgPerformanceMemoryTest
from image.performance.stress_ng_general import (
    StressNgCombineLoadTest,
    StressNgConsecutiveLoadTest,
    StressNgIterTestIPC,
    StressNgParallelLoadTest,
)
from image.performance.syscalls import (
    StressNgSyscallsWithMemLoadTest,
    SyscallsFullLoadTest,
    SyscallsWithCpuLoadTest,
)
from image.performance.system import PTSSystemTest
from imgtests.constant import CONFIG_DIR
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
from imgtests.suites.fault_injection import (
    FaultInjectionChaosbladeTest,
    FaultInjectionEnduranceTest,
)
from imgtests.suites.general.joint_bench import JointBench
from imgtests.suites.general.std_utils import POSIXUtilsTest
from imgtests.suites.network import (
    Iperf3LocalTest,
    Iperf3PacketRateScalingTest,
    StressNgEnduranceNetworkTest,
    StressNgMaxNetworkLoadTest,
)
from imgtests.types import Subsystem

if TYPE_CHECKING:
    from collections.abc import Iterable


ALL_SUBSYSTEMS_SUITE: Final = TestsRunnerConfig(
    description="Test suite for all subsystems.",
    tests=(
        JointBench(iterations=3),
        SchedPerformanceTest(3),
        POSIXUtilsTest(10),
        FioDisksScalingTest,
        FioDisksNightly,
        FioDisksDMDelay,
        FioDisksDMDust,
        LTPSyscallsTest,
        StressNgEnduranceSyscallsTest,
        Iperf3LocalTest,
        Iperf3PacketRateScalingTest,
        StressNgMaxNetworkLoadTest,
        StressNgEnduranceNetworkTest,
        StressNgPerformanceCpuTest,
        ChaosbladeCPUTest,
        PTSSystemTest(2),
        StressNgIterTestIPC,
        StressNgConsecutiveLoadTest,
        StressNgCombineLoadTest,
        StressNgParallelLoadTest,
        StressNgEnduranceMemoryTest,
        StressNgPerformanceMemoryTest,
        SarWithStressNGTest,
        FaultInjectionEnduranceTest,
        FaultInjectionChaosbladeTest,
    ),
    experiment_type="performance",
    duration=1200,
    install_dependencies=True,
)
MEMORY_SUITE: Final = TestsRunnerConfig(
    description="Test suite for virtual memory.",
    tests=(
        StressNgEnduranceMemoryTest,
        StressNgPerformanceMemoryTest,
        SarWithStressNGTest,
    ),
    experiment_type="performance",
    duration=100,
    install_dependencies=True,
)
SYSCALLS_SUITE: Final = TestsRunnerConfig(
    description="Test suite for syscalls.",
    tests=(
        StressNgEnduranceSyscallsTest,
        LTPSyscallsTest,
        SyscallsWithCpuLoadTest,
        StressNgSyscallsWithMemLoadTest,
        SyscallsFullLoadTest,
        StressNgIterTestIPC,
    ),
    experiment_type="performance",
    duration=200,
    install_dependencies=True,
)
IPC_SUITE: Final = TestsRunnerConfig(
    description="Test suite for IPC subsystem.",
    tests=(
        LTPSyscallsIPCTest,
        JointBench(subsystems=frozenset({Subsystem.IPC}), iterations=3),
        StressNgIterTestIPC,
    ),
    experiment_type="performance",
    duration=100,
    install_dependencies=True,
)
NETWORK_SUITE: Final = TestsRunnerConfig(
    description="Test suite for network subsystem.",
    tests=(
        Iperf3LocalTest,
        Iperf3PacketRateScalingTest,
        StressNgMaxNetworkLoadTest,
        StressNgEnduranceNetworkTest,
    ),
    experiment_type="performance",
    duration=200,
    install_dependencies=True,
)
FILE_SUITE: Final = TestsRunnerConfig(
    description="Test suite for file subsystem.",
    tests=(
        FioDisksVariationTest,
        FioDisksParallelLoadTest,
        FioDisksNightly,
        FioDisksScalingTest,
        FioDisksDMDust,
        FioDisksDMDelay,
    ),
    experiment_type="performance",
    duration=300,
    install_dependencies=True,
)
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


def load_test_config(tested_distro: str) -> dict[str, Any]:
    config_file = CONFIG_DIR / f"{tested_distro}_config.json"
    if config_file.exists():
        try:
            with Path.open(config_file, "r") as f:
                config = json.load(f)
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to load config: %s, using default", e)
        else:
            logger.info("Loaded custom config for %s", tested_distro)
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


def get_test_name(
    test: AbstractRunnableManyTimesTest | type[AbstractRunnableTimeLimitedTest],
) -> str:
    if hasattr(test, "__name__"):
        return test.__name__
    if hasattr(test, "__class__"):
        return test.__class__.__name__
    return str(test)


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


def main() -> None:  # noqa: PLR0912, PLR0915, C901
    set_handlers(logger, Path("processing.log"))
    tested_distro = os.getenv("TESTED_DISTRO", "all")
    if tested_distro not in ("all", "yocto", "opensuse"):
        logger.error(
            "Invalid TESTED_DISTRO value: %s. Use 'all', 'yocto', 'opensuse'",
            tested_distro,
        )
        sys.exit(1)
    logger.info("Running tests for %s", tested_distro)
    config = load_test_config(tested_distro)
    logger.info("Using suites: %s", config.get("suites", []))
    suites_to_run = []
    suites_map = {
        "FILE_SUITE": FILE_SUITE,
        "MEMORY_SUITE": MEMORY_SUITE,
        "SYSCALLS_SUITE": SYSCALLS_SUITE,
        "IPC_SUITE": IPC_SUITE,
        "NETWORK_SUITE": NETWORK_SUITE,
    }
    for suite_name in config.get("suites", []):
        if suite_name in suites_map:
            suite = suites_map[suite_name]

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
    if tested_distro in ("yocto", "all"):
        poky_client = wait_remote(*YOCTO_CONF) or sys.exit(1)
    if tested_distro in ("opensuse", "all"):
        suse_client = wait_remote(*SUSE_156_CONF) or sys.exit(1)
        # disable cloud-init for the next boot for Suse according to documentation
        Touch(suse_client, use_sudo=True)(["/etc/cloud/cloud-init.disabled"])
    distros_to_test = []
    if suse_client:
        distros_to_test.append(suse_client)
    if poky_client:
        distros_to_test.append(poky_client)
    database = ImgtestsDatabase()
    for suite in suites_to_run:
        logger.info("Running suite %s", suite.description)
        for client in distros_to_test:
            client.reconnect()
            runner = TestsRunner(client, database, suite)
            runner.run()
            runner.close()
    if poky_client:
        poky_client.reconnect()
        ProfiledPlanRunner(
            client=poky_client,
            database=database,
        ).run_from_env()
        poky_client.close()
    if suse_client:
        suse_client.reconnect()
        ProfiledPlanRunner(
            client=suse_client,
            database=database,
        ).run_from_env()
        suse_client.close()

    report_generator = ReportGenerator(database)
    report_generator.generate_last_two_experiments_report(out_dir=Path("results"))

    database.session.close_all()


if __name__ == "__main__":
    main()
