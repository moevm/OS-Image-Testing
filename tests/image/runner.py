import logging
import sys
from pathlib import Path
from typing import Final

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
from imgtests.database.database import ImgtestsDatabase
from imgtests.exec.exec import wait_remote
from imgtests.exec.user_commands import Touch
from imgtests.logger import set_handlers
from imgtests.reporting.html_report import ReportGenerator
from imgtests.runner import ProfiledPlanRunner, TestsRunner, TestsRunnerConfig
from imgtests.suites.fault_injection import FaultInjectionEnduranceTest
from imgtests.suites.general.joint_bench import JointBench
from imgtests.suites.general.std_utils import POSIXUtilsTest
from imgtests.suites.network import (
    Iperf3LocalTest,
    Iperf3PacketRateScalingTest,
    StressNgEnduranceNetworkTest,
    StressNgMaxNetworkLoadTest,
)
from imgtests.types import Subsystem

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


def main() -> None:
    logger = logging.getLogger()
    set_handlers(logger, Path("processing.log"))
    suse_client = wait_remote(*SUSE_156_CONF) or sys.exit(1)
    # disable cloud-init for the next boot for Suse according to documentation
    Touch(suse_client, use_sudo=True)(["/etc/cloud/cloud-init.disabled"])
    poky_client = wait_remote(*YOCTO_CONF) or sys.exit(1)
    database = ImgtestsDatabase()
    for suite in (
        FILE_SUITE,
        MEMORY_SUITE,
        SYSCALLS_SUITE,
        IPC_SUITE,
        NETWORK_SUITE,
        ALL_SUBSYSTEMS_SUITE,
    ):
        suse_client.reconnect()
        suse_runner = TestsRunner(suse_client, database, suite)
        suse_runner.run()
        suse_runner.close()
        poky_client.reconnect()
        yocto_runner = TestsRunner(poky_client, database, suite)
        yocto_runner.run()
        yocto_runner.close()

    poky_client.reconnect()
    ProfiledPlanRunner(
        client=poky_client,
        database=database,
    ).run_from_env()
    poky_client.close()
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
