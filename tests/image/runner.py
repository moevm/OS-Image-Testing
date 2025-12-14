import logging
import sys
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Thread
from time import sleep
from typing import Any, Final

import paramiko
import paramiko.ssh_exception

from image.endurance.syscalls import run_ltp_syscalls
from image.performance.cpu import run_stress_ng_tests
from image.performance.system import run_pts_tests
from image.utils import env_var_to_type_or_exit
from imgtests.exec.exec import SSHClient
from imgtests.logger import set_handlers
from imgtests.sysrep import SystemInfo, compare_system_infos, get_system_info

logger = logging.getLogger()
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


def is_remote_alive(client: SSHClient, executor: ThreadPoolExecutor) -> None:
    while True:
        sleep(30)
        try:
            client(["echo", "yes"])
        except paramiko.ssh_exception.SSHException:
            break
    executor.shutdown(cancel_futures=True)
    logger.error("Remote node unavailable during test.")
    sys.exit(1)


def main() -> None:
    executor = ThreadPoolExecutor()
    client = wait_remote()
    if client is None:
        logger.error("Failed to connect to the remote node.")
        sys.exit(1)
    is_alive_cycle = Thread(target=is_remote_alive, args=(client, executor))
    is_alive_cycle.start()
    futures: list[Future[Any]] = []
    futures.append(executor.submit(get_system_info))
    futures.append(executor.submit(get_system_info, client))
    sys_infos: list[SystemInfo] = []
    for future in as_completed(futures):
        result = future.result()
        sys_infos.append(result)
        logger.info(result.tools_versions)
        logger.info(result.uname_info)
        logger.info("Packages count %d", len(result.package_list))
    logger.info(compare_system_infos(*sys_infos))
    run_pts_tests(executor, client)
    run_stress_ng_tests(executor, client)
    run_ltp_syscalls(executor, client)
    logger.info("All tests completed successfully")
    is_alive_cycle.join()


if __name__ == "__main__":
    main()
