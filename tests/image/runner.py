import logging
import sys
from pathlib import Path
from typing import Final

from image.endurance.memory import StressNgEnduranceMemoryTest
from image.endurance.network import WgetEnduranceNetworkTest
from image.endurance.syscalls import (
    LTPSyscallsTest,
    StressNgEnduranceSyscallsTest,
)
from image.performance.cpu import ChaosbladeCPUTest, StressNgPerformanceCpuTest
from image.performance.fio_disks import (
    FioDisksDMDelay,
    FioDisksDMDust,
    FioDisksNightly,
    FioDisksScalingTest,
)
from image.performance.ipc import SchedPerformanceTest
from image.performance.memory import SarWithStressNGTest, StressNgPerformanceMemoryTest
from image.performance.network import Iperf3LocalTest
from image.performance.std_utils import POSIXUtilsTest
from image.performance.stress_ng_general import (
    StressNgCombineLoadTest,
    StressNgConsecutiveLoadTest,
    StressNgParallelLoadTest,
)
from image.performance.syscalls import (
    StressNgSyscallsWithMemLoadTest,
    SyscallsFullLoadTest,
    SyscallsWithCpuLoadTest,
)
from image.performance.system import PTSSystemTest
from imgtests.exec.exec import wait_remote
from imgtests.logger import set_handlers
from imgtests.runner import TestsRunner, TestsRunnerConfig
from imgtests.suites.general.joint_bench import JointBench
from imgtests.suites.system import SystemLoadTimeTest, SystemSlowServicesTest

ALL_SUBSYSTEMS_SUITE: Final = TestsRunnerConfig(
    description="Test suite for all subsystems.",
    tests=(
        SystemLoadTimeTest(),
        SystemSlowServicesTest(),
        JointBench(iterations=3),
        SchedPerformanceTest(3),
        POSIXUtilsTest(10),
        FioDisksScalingTest(10),
        FioDisksNightly(10),
        FioDisksDMDelay(30),
        FioDisksDMDust(30),
        LTPSyscallsTest(),
        StressNgEnduranceSyscallsTest(60),
        WgetEnduranceNetworkTest(5),
        Iperf3LocalTest(30),
        StressNgPerformanceCpuTest(60),
        ChaosbladeCPUTest(60),
        PTSSystemTest(2),
        StressNgConsecutiveLoadTest(30),
        StressNgCombineLoadTest(10),
        StressNgParallelLoadTest(30),
        StressNgEnduranceMemoryTest(60),
        StressNgPerformanceMemoryTest(30),
        SarWithStressNGTest(60),
    ),
    experiment_type="all",
    install_dependencies=True,
)
SYSCALLS_SUITE: Final = TestsRunnerConfig(
    description="Test suite for syscalls.",
    tests=(
        StressNgEnduranceSyscallsTest(60),
        LTPSyscallsTest(),
        SyscallsWithCpuLoadTest(600),
        StressNgSyscallsWithMemLoadTest(60),
        SyscallsFullLoadTest(600),
    ),
    experiment_type="all",
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
    suse_runner = TestsRunner(
        wait_remote(*SUSE_156_CONF) or sys.exit(1),
        ALL_SUBSYSTEMS_SUITE,
    )
    suse_runner.run()
    yocto_runner = TestsRunner(
        wait_remote(*YOCTO_CONF) or sys.exit(1),
        ALL_SUBSYSTEMS_SUITE,
    )
    yocto_runner.run()


if __name__ == "__main__":
    main()
