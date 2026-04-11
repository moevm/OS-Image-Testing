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
from image.performance.network import Iperf3LocalTest
from image.performance.std_utils import POSIXUtilsTest
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
from imgtests.logger import set_handlers
from imgtests.runner import ProfiledPlanRunner, TestsRunner, TestsRunnerConfig
from imgtests.suites.fault_injection import FaultInjectionEnduranceTest
from imgtests.suites.general.joint_bench import JointBench
from imgtests.suites.system import (
    SystemLoadTimeTest,
    SystemSlowServicesTest,
)
from imgtests.types import Subsystem

ALL_SUBSYSTEMS_SUITE: Final = TestsRunnerConfig(
    description="Test suite for all subsystems.",
    tests=(
        SystemLoadTimeTest(),
        SystemSlowServicesTest(),
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
    experiment_type="all",
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
    experiment_type="all",
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
    experiment_type="all",
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
    experiment_type="all",
    duration=100,
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
    experiment_type="all",
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
    poky_client = wait_remote(*YOCTO_CONF) or sys.exit(1)
    database = ImgtestsDatabase()
    for suite in (FILE_SUITE, MEMORY_SUITE, SYSCALLS_SUITE, IPC_SUITE, ALL_SUBSYSTEMS_SUITE):
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
    suse_client.close()
    poky_client.close()
    database.session.close_all()


if __name__ == "__main__":
    main()
