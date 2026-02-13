import logging
import sys
from pathlib import Path

from image.endurance.syscalls import test_ltp_syscalls, test_syscalls_all_stress_ng
from image.performance.cpu import test_chaosblade_cpu, test_stress_ng_cpu
from image.performance.ipc import test_sched
from image.performance.network import test_iperf3
from image.performance.system import test_pts_system
from imgtests.exec.exec import wait_remote
from imgtests.logger import set_handlers
from imgtests.runner import TestConfig, TestRunner

logger = logging.getLogger()
set_handlers(logger, Path("processing.log"))


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
    client = wait_remote(*yocto_conf) or sys.exit(1)
    runner = TestRunner(
        client,
        TestConfig(
            tests=(
                test_iperf3,
                test_pts_system,
                test_stress_ng_cpu,
                test_chaosblade_cpu,
                test_syscalls_all_stress_ng,
                test_ltp_syscalls,
                test_sched,
            )
        ),
        logger,
    )
    runner.run()


if __name__ == "__main__":
    main()
