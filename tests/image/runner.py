import logging
import sys
from pathlib import Path

from image.endurance.network import WgetEnduranceNetworkTest
from image.endurance.syscalls import (
    LTPSyscallsTest,
    StressNgEnduranceSyscallsTest,
)
from image.performance.cpu import ChaosbladeCPUTest, StressNgPerformanceCpuTest
from image.performance.fio_disks import FioDisksNightly, FioDisksScalingTest
from image.performance.ipc import SchedPerformanceTest
from image.performance.network import Iperf3LocalTest
from image.performance.std_utils import POSIXUtilsTest
from image.performance.stress_ng_general import (
    StressNgCombineLoadTest,
    StressNgConsecutiveLoadTest,
    StressNgParallelLoadTest,
)
from image.performance.system import PTSSystemTest
from imgtests.exec.exec import wait_remote
from imgtests.logger import set_handlers
from imgtests.runner import TestsRunner, TestsRunnerConfig
from imgtests.suites.general.joint_bench import JointBench
from imgtests.suites.system import SystemLoadTimeTest, SystemSlowServicesTest

yocto_conf = (
    "SSH_YOCTO_ADDR",
    "SSH_YOCTO_USER",
    "SSH_YOCTO_PASS",
    "SSH_YOCTO_PORT",
)
suse_156_conf = (
    "SSH_SUSE_ADDR_156",
    "SSH_SUSE_USER",
    "SSH_SUSE_PASS",
    "SSH_SUSE_PORT_156",
)


def main() -> None:
    logger = logging.getLogger()
    set_handlers(logger, Path("processing.log"))
    all_subsystems_suite = TestsRunnerConfig(
        description="Test suite for all subsystems.",
        tests=(
            SystemLoadTimeTest(),
            SystemSlowServicesTest(),
            JointBench(iterations=3),
            SchedPerformanceTest(3),
            POSIXUtilsTest(10),
            FioDisksScalingTest(10),
            FioDisksNightly(10),
            WgetEnduranceNetworkTest(5),
            Iperf3LocalTest(30),
            StressNgPerformanceCpuTest(60),
            ChaosbladeCPUTest(60),
            LTPSyscallsTest(),
            StressNgEnduranceSyscallsTest(60),
            PTSSystemTest(2),
            StressNgConsecutiveLoadTest(30),
            StressNgCombineLoadTest(10),
            StressNgParallelLoadTest(30),
        ),
        experiment_type="all",
        install_dependencies=True,
    )
    suse_runner = TestsRunner(
        wait_remote(*suse_156_conf) or sys.exit(1),
        all_subsystems_suite,
    )
    suse_runner.run()
    yocto_runner = TestsRunner(
        wait_remote(*yocto_conf) or sys.exit(1),
        all_subsystems_suite,
    )
    yocto_runner.run()


if __name__ == "__main__":
    main()
