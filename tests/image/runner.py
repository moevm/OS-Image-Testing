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


SSH_YOCTO_PASSWORD: Final = env_var_to_type_or_exit("SSH_YOCTO_PASS", str, logger)
SSH_YOCTO_USER: Final = env_var_to_type_or_exit("SSH_YOCTO_USER", str, logger)
SSH_YOCTO_ADDR: Final = env_var_to_type_or_exit("SSH_YOCTO_ADDR", str, logger)
SSH_YOCTO_PORT: Final = env_var_to_type_or_exit("SSH_YOCTO_PORT", int, logger)
SSH_SUSE_PASSWORD: Final = env_var_to_type_or_exit("SSH_SUSE_PASS", str, logger)
SSH_SUSE_USER: Final = env_var_to_type_or_exit("SSH_SUSE_USER", str, logger)
SSH_SUSE_ADDR_155: Final = env_var_to_type_or_exit("SSH_SUSE_ADDR_155", str, logger)
SSH_SUSE_PORT_155: Final = env_var_to_type_or_exit("SSH_SUSE_PORT_155", int, logger)
SSH_SUSE_ADDR_156: Final = env_var_to_type_or_exit("SSH_SUSE_ADDR_156", str, logger)
SSH_SUSE_PORT_156: Final = env_var_to_type_or_exit("SSH_SUSE_PORT_156", int, logger)


def wait_remote(addr: str, user: str, password: str, port: int) -> SSHClient:
    wait_sec = 60 * 60 * 5
    step_sec = 60
    while wait_sec > 0:
        try:
            return SSHClient(addr, user, password, port)
        except paramiko.ssh_exception.SSHException:
            logger.info("Waiting remote node to build and run image.")
        sleep(step_sec)
        wait_sec -= 60
    logger.error("Failed to connect to the remote node.")
    sys.exit(1)


def is_remote_alive(client: SSHClient, executor: ThreadPoolExecutor) -> None:
    while True:
        sleep(30)
        try:
            client(["echo", "test"])
        except paramiko.ssh_exception.SSHException:
            break
    executor.shutdown(cancel_futures=True)
    logger.error("Remote node unavailable during test.")
    sys.exit(1)


def main() -> None:
    executor = ThreadPoolExecutor()
    client = wait_remote(SSH_YOCTO_ADDR, SSH_YOCTO_USER, SSH_YOCTO_PASSWORD, SSH_YOCTO_PORT)
    suse155 = wait_remote(SSH_SUSE_ADDR_155, SSH_SUSE_USER, SSH_SUSE_PASSWORD, SSH_SUSE_PORT_155)
    suse156 = wait_remote(SSH_SUSE_ADDR_156, SSH_SUSE_USER, SSH_SUSE_PASSWORD, SSH_SUSE_PORT_156)
    suse155(["echo", "test"])
    suse156(["echo", "test"])
    is_alive_cycle = Thread(target=is_remote_alive, args=(client, executor))
    is_alive_cycle.start()
    futures: list[Future[Any]] = []
    futures.append(executor.submit(get_system_info, client))
    futures.append(executor.submit(get_system_info, suse155))
    futures.append(executor.submit(get_system_info, suse156))
    sys_infos: list[SystemInfo] = []
    for future in as_completed(futures):
        result = future.result()
        sys_infos.append(result)
        logger.info(result.tools_versions)
        logger.info(result.uname_info)
        logger.info("Packages count %d", len(result.package_list))
    logger.info(compare_system_infos(sys_infos[0], sys_infos[1]))
    logger.info(compare_system_infos(sys_infos[0], sys_infos[2]))
    logger.info(compare_system_infos(sys_infos[1], sys_infos[2]))
    run_pts_tests(executor, client)
    run_stress_ng_tests(executor, client)
    run_ltp_syscalls(executor, client)
    logger.info("All tests completed successfully")
    is_alive_cycle.join()


if __name__ == "__main__":
    main()
