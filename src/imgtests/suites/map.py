from typing import Final

from imgtests.runner import TestsRunnerConfig
from imgtests.suites.drive.fio_file import (
    FioDisksDMDelay,
    FioDisksDMDust,
    FioDisksNightly,
    FioDisksParallelLoadTest,
    FioDisksScalingTest,
    FioDisksVariationTest,
)
from imgtests.suites.drive.stress_ng import StressNgEnduranceFileTest
from imgtests.suites.fault_injection import (
    FaultInjectionChaosbladeTest,
    FaultInjectionEnduranceTest,
    FaultInjectionFioTest,
    FaultInjectionPerfTest,
    FaultInjectionStressNgTest,
)
from imgtests.suites.general.joint_bench import JointBench
from imgtests.suites.general.std_utils import POSIXUtilsTest
from imgtests.suites.general.stress_ng_general import (
    StressNgCombineLoadTest,
    StressNgConsecutiveLoadTest,
    StressNgParallelLoadTest,
)
from imgtests.suites.ipc import LTPSyscallsIPCTest, SchedPerformanceTest, StressNgIterTestIPC
from imgtests.suites.memory import (
    SarWithStressNgTest,
    StressNgEnduranceMemoryTest,
    StressNgPerformanceMemoryTest,
)
from imgtests.suites.network import (
    Iperf3LocalTest,
    Iperf3PacketRateScalingTest,
    StressNgEnduranceNetworkTest,
    StressNgMaxNetworkLoadTest,
)
from imgtests.suites.syscalls import (
    LTPSyscallsTest,
    StressNgEnduranceSyscallsTest,
    StressNgSyscallsWithMemLoadTest,
    SyscallsFullLoadTest,
    SyscallsWithCpuLoadTest,
)
from imgtests.suites.system import (
    ChaosbladeCPUTest,
    PTSSystemTest,
    StressNgEnduranceCpuTest,
    StressNgPerformanceCpuTest,
)
from imgtests.types import Subsystem

ALL_SUBSYSTEMS_SUITE: Final = TestsRunnerConfig(
    description="Test suite for all subsystems.",
    tests=(
        JointBench(iterations=3),
        SchedPerformanceTest(3),
        POSIXUtilsTest(10),
        StressNgEnduranceFileTest,
        FioDisksScalingTest,
        FioDisksNightly,
        FioDisksDMDelay,
        FioDisksDMDust,
        LTPSyscallsTest,
        StressNgEnduranceSyscallsTest,
        StressNgEnduranceCpuTest,
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
        SarWithStressNgTest,
        FaultInjectionEnduranceTest,
        FaultInjectionChaosbladeTest,
        FaultInjectionStressNgTest,
        FaultInjectionPerfTest,
        FaultInjectionFioTest,
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
        SarWithStressNgTest,
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
        StressNgEnduranceFileTest,
        FioDisksVariationTest,
        FioDisksParallelLoadTest,
        FioDisksNightly,
        FioDisksScalingTest,
        FioDisksDMDust,
        FioDisksDMDelay,
    ),
    experiment_type="performance",
    duration=400,
    install_dependencies=True,
)
ALL_SUITES: Final = {
    "FILE_SUITE": FILE_SUITE,
    "MEMORY_SUITE": MEMORY_SUITE,
    "SYSCALLS_SUITE": SYSCALLS_SUITE,
    "IPC_SUITE": IPC_SUITE,
    "NETWORK_SUITE": NETWORK_SUITE,
}
