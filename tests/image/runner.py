import logging
import sys
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Thread
from time import sleep
from typing import TYPE_CHECKING, Any

import paramiko
import paramiko.ssh_exception

from image.endurance.syscalls import test_ltp_syscalls, test_syscalls_all_stress_ng
from image.performance.cpu import run_chaosblade_tests, run_stress_ng_tests
from image.performance.ipc import test_sched
from image.performance.system import test_pts_system

if TYPE_CHECKING:
    from imgtests.exec.base_util import BaseTestUtil
from imgtests.database.database import Database
from imgtests.exec.exec import SSHClient, wait_remote
from imgtests.logger import set_handlers
from imgtests.sysrep import SystemInfo, compare_system_infos, get_os_release, get_system_info
from imgtests.types import Distro

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


def is_remote_alive(client: SSHClient, executor: ThreadPoolExecutor) -> None:
    while True:
        sleep(30)
        try:
            client(["echo", "test"])
        except paramiko.ssh_exception.SSHException:
            break
    executor.shutdown(cancel_futures=True)
    logger.error("Remote node unavailable during test.")


def suse_install_dependencies(client: SSHClient) -> None:
    os_id = get_os_release(client).id
    if not (os_id and os_id == Distro.OPEN_SUSE_LEAP.value):
        logger.error("Required openSUSE LEAP to install dependencies. Provided %s.", os_id)
        return
    from imgtests.exec.loaders import (  # noqa: PLC0415
        Chaosblade,
        Fio,
        FioPlot,
        Kirk,
        Perf,
        PhoronixTestSuite,
        StressNg,
    )

    tool: BaseTestUtil
    for tool in [Chaosblade, Fio, FioPlot, Kirk, Perf, StressNg, PhoronixTestSuite]:
        tool_instance = tool(client)
        try:
            tool_instance.install()
        except NotImplementedError:
            logger.exception("Failed to install dependencies.")
            continue
        tool_instance = tool(client)
        logger.info(
            "Installed '%s' with version '%s'.", tool_instance.name, tool_instance.version()
        )


def run_tests(executor: ThreadPoolExecutor, client: SSHClient) -> None:
    test_pts_system(executor, client)
    run_stress_ng_tests(executor, client)
    run_chaosblade_tests(executor, client)
    future = executor.submit(test_syscalls_all_stress_ng, client)
    future.result()
    future = executor.submit(test_ltp_syscalls, client)
    future.result()
    future = executor.submit(test_sched, client)
    future.result()
    logger.info("All tests completed successfully")


def main() -> None:
    db_inst = Database()
    executor = ThreadPoolExecutor()
    client = wait_remote(*yocto_conf) or sys.exit(1)
    suse156 = wait_remote(*suse_156_conf) or sys.exit(1)
    suse156(["echo", "test"])
    is_alive_cycle = Thread(target=is_remote_alive, args=(client, executor))
    is_alive_cycle.start()
    futures: list[Future[Any]] = []
    futures.append(executor.submit(get_system_info, client))
    futures.append(executor.submit(get_system_info, suse156))
    sys_infos: list[SystemInfo] = []
    for future in as_completed(futures):
        result = future.result()
        sys_infos.append(result)
        logger.info(result.tools_versions)
        logger.info(result.uname_info)
        logger.info("Packages count %d", len(result.package_list))
        db_inst.insert_from_system_info(result)
    logger.info(compare_system_infos(sys_infos[0], sys_infos[1]))
    run_tests(executor, client)
    is_alive_cycle.join()


if __name__ == "__main__":
    main()
