import logging
import sys
from pathlib import Path
from time import sleep
from typing import TYPE_CHECKING

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
from imgtests.exec.exec import SSHClient, wait_remote
from imgtests.exec.observers.systemd_analyze import SystemdAnalyze
from imgtests.logger import set_handlers
from imgtests.runner import AbstractRunnableManyTimesTest, TestsRunner, TestsRunnerConfig

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor


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


class SystemLoadTimeTest(AbstractRunnableManyTimesTest):
    def __init__(self) -> None:
        super().__init__("System load time.", {"system"})

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        iterations: int,  # noqa: ARG002
    ) -> None:
        result = SystemdAnalyze(client).time()
        sleep_time_sec = 10
        wait_timeout_sec = 600
        while result.total_time < 0 and wait_timeout_sec > 0:
            self.logger.info(
                "Waiting for system to be ready to analyze boot time, %d seconds left.",
                wait_timeout_sec,
            )
            sleep(sleep_time_sec)
            wait_timeout_sec -= sleep_time_sec
            result = SystemdAnalyze(client).time()
        if result.total_time < 0:
            self.logger.error("Failed to get boot time, system might not be ready.")


class SystemSlowServicesTest(AbstractRunnableManyTimesTest):
    def __init__(self) -> None:
        super().__init__("System slow services.", {"system"})

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        iterations: int,  # noqa: ARG002
    ) -> None:
        self.logger.info(SystemdAnalyze(client).slow_load_services())


def main() -> None:
    logger = logging.getLogger()
    set_handlers(logger, Path("processing.log"))
    suse_runner = TestsRunner(
        wait_remote(*suse_156_conf) or sys.exit(1),
        TestsRunnerConfig(
            description="Empty test suite.",
            tests=(
                SystemLoadTimeTest(),
                SystemSlowServicesTest(),
                POSIXUtilsTest(10),
            ),
            experiment_type="performance",
            install_dependencies=True,
        ),
    )
    suse_runner.run()
    yocto_runner = TestsRunner(
        wait_remote(*yocto_conf) or sys.exit(1),
        TestsRunnerConfig(
            description="Test suite for all subsystems.",
            tests=(
                POSIXUtilsTest(10),
                FioDisksScalingTest(10),
                FioDisksNightly(10),
                Iperf3LocalTest(30),
                StressNgPerformanceCpuTest(60),
                ChaosbladeCPUTest(60),
                LTPSyscallsTest(),
                StressNgEnduranceSyscallsTest(60),
                SchedPerformanceTest(3),
                PTSSystemTest(2),
                StressNgConsecutiveLoadTest(30),
                StressNgCombineLoadTest(10),
                StressNgParallelLoadTest(30),
            ),
            experiment_type="all",
        ),
    )
    yocto_runner.run()


if __name__ == "__main__":
    main()
