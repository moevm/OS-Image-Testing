import logging
import sys
from pathlib import Path

from image.endurance.syscalls import test_ltp_syscalls, test_syscalls_all_stress_ng
from image.performance.cpu import test_chaosblade_cpu, test_stress_ng_cpu
from image.performance.fio_disks import test_fio_disks_scaling
from image.performance.ipc import test_sched
from image.performance.network import test_iperf3
from image.performance.std_utils import test_all_tools
from image.performance.system import test_pts_system
from imgtests.exec.exec import wait_remote
from imgtests.exec.observers.systemd_analyze import SystemdAnalyze
from imgtests.logger import set_handlers
from imgtests.runner import RunnableTest, TestsRunner, TestsRunnerConfig

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
    suse_runner = TestsRunner(
        wait_remote(*suse_156_conf) or sys.exit(1),
        TestsRunnerConfig(
            description="Empty test suite.",
            tests=(
                RunnableTest(
                    description="System load time.",
                    subsystems={"system"},
                    test_func=lambda _, client: logger.info(SystemdAnalyze(client).time()),
                    test_kwargs={},
                ),
                RunnableTest(
                    description="System slow services.",
                    subsystems={"system"},
                    test_func=lambda _, client: logger.info(
                        SystemdAnalyze(client).slow_load_services()
                    ),
                    test_kwargs={},
                ),
            ),
            experiment_type="performance",
        ),
    )
    suse_runner.run()
    yocto_runner = TestsRunner(
        wait_remote(*yocto_conf) or sys.exit(1),
        TestsRunnerConfig(
            description="Test suite for all subsystems.",
            tests=(
                RunnableTest(
                    description="Load drives with fio.",
                    subsystems={"file"},
                    test_func=lambda executor, client: test_fio_disks_scaling(
                        executor,
                        client,
                        10,
                        Path().home(),
                    ),
                    test_kwargs={},
                ),
                TestSpec(
                    description="Test standard utilities.",
                    subsystems=("system",),
                    test_func=test_all_tools,
                    test_kwargs={"iterations": 10},
                ),
                RunnableTest(
                    description="Load local network with iperf3.",
                    subsystems={"network"},
                    test_func=test_iperf3,
                    test_kwargs={},
                ),
                RunnableTest(
                    description="Load CPU with stress-ng.",
                    subsystems={"system"},
                    test_func=test_stress_ng_cpu,
                    test_kwargs={},
                ),
                RunnableTest(
                    description="Load CPU with chaosblade.",
                    subsystems={"system"},
                    test_func=test_chaosblade_cpu,
                    test_kwargs={},
                ),
                RunnableTest(
                    description="Test syscalls performance.",
                    subsystems={"syscalls"},
                    test_func=test_syscalls_all_stress_ng,
                    test_kwargs={},
                ),
                RunnableTest(
                    description="Test syscalls with LTP.",
                    subsystems={"syscalls"},
                    test_func=test_ltp_syscalls,
                    test_kwargs={},
                ),
                RunnableTest(
                    description="Benchmark sheduler and IPC mechanisms.",
                    subsystems={"IPC"},
                    test_func=test_sched,
                    test_kwargs={},
                ),
                RunnableTest(
                    description="Load system with PTS.",
                    subsystems={"system"},
                    test_func=test_pts_system,
                    test_kwargs={},
                ),
            ),
            experiment_type="all",
        ),
    )
    yocto_runner.run()


if __name__ == "__main__":
    main()
