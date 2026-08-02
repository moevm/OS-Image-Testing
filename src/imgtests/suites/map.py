from typing import TYPE_CHECKING, Final

from imgtests.planning import (
    AbstractRunnableManyTimesTest,
    AbstractRunnableTimeLimitedTest,
)
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
    FaultInjectionIperf3Test,
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

if TYPE_CHECKING:
    from collections.abc import Sequence

    from imgtests.database.models.experiment import ExperimentType


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
        FaultInjectionIperf3Test,
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
