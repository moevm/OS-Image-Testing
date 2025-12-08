import logging
from pathlib import Path
from time import sleep
from typing import Final

import paramiko
import paramiko.ssh_exception

from image.utils import env_var_to_type_or_exit
from imgtests.exec.exec import SSHClient
from imgtests.exec.loaders.pts import PhoronixTestSuite, setup_pts
from imgtests.exec.loaders.stress_ng import StressNg
from imgtests.logger import set_handlers
from imgtests.sysrep import get_system_info

logger = logging.getLogger(__name__)
set_handlers(logger, Path("processing.log"))


SSH_PASSWORD: Final = env_var_to_type_or_exit("SSH_PASS", str, logger)
SSH_USER: Final = env_var_to_type_or_exit("SSH_USER", str, logger)
SSH_ADDR: Final = env_var_to_type_or_exit("SSH_ADDR", str, logger)
SSH_PORT: Final = env_var_to_type_or_exit("SSH_PORT", int, logger)


def wait_remote() -> SSHClient | None:
    wait_sec = 60 * 60 * 5
    step_sec = 60
    while wait_sec > 0:
        try:
            return SSHClient(SSH_ADDR, SSH_USER, SSH_PASSWORD, SSH_PORT)
        except paramiko.ssh_exception.SSHException:
            logger.info("Waiting remote node to build and run image.")
        sleep(step_sec)
        wait_sec -= 60
    return None


if __name__ == "__main__":
    client = wait_remote()

    stress_ng = StressNg(client)
    pts = PhoronixTestSuite(client)

    system_info = get_system_info(client)
    logger.info(system_info.tools_versions)
    logger.info(system_info.uname_info)
    logger.info("Packages count %d", len(system_info.package_list))

    _, stress_ng_metrics = stress_ng.run(timeout_sec=20, cpu=1)
    logger.info(stress_ng_metrics)

    setup_pts(client)
    pts_metrics = pts.run(test_name="pts/pybench", run_count=1)
    logger.info(pts_metrics)
