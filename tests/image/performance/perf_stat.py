import logging
from typing import TYPE_CHECKING

from imgtests.exec.loaders import Perf

if TYPE_CHECKING:
    from imgtests.exec.exec import SSHClient

logger = logging.getLogger(__name__)


def test_perf_stat_cpu_stress_ng(client: SSHClient | None) -> None:
    perf = Perf(client)
    r = perf(
        [
            "stat",
            "-e",
            "context-switches,cpu-migrations,page-faults,cpu-clock",
            "--",
            "stress-ng",
            "--cpu",
            "0",
            "--cpu-method",
            "matrixprod",
            "--timeout",
            "60s",
            "--metrics-brief",
            "--oom-avoid",
        ]
    )

    if r.returncode:
        logger.error("perf stat cpu stress-ng FAILED")
    else:
        logger.info("perf stat cpu stress-ng PASSED")


def test_perf_stat_disks_stress_ng(client: SSHClient | None) -> None:
    perf = Perf(client)
    r = perf(
        [
            "stat",
            "-e",
            "block:block_rq_issue,block:block_rq_complete,block:block_rq_insert,block:block_io_done,cpu-clock",
            "--",
            "stress-ng",
            "--hdd",
            "2",
            "--hdd-bytes",
            "100M",
            "--timeout",
            "60s",
            "--metrics-brief",
            "--oom-avoid",
        ]
    )

    if r.returncode:
        logger.error("perf stat disks stress-ng FAILED")
    else:
        logger.info("perf stat disks stress-ng PASSED")


def test_perf_stat_memory_stress_ng(client: SSHClient | None) -> None:
    perf = Perf(client)
    r = perf(
        [
            "stat",
            "-e",
            "page-faults,minor-faults,major-faults,context-switches",
            "--",
            "stress-ng",
            "--vm",
            "1",
            "--vm-bytes",
            "10%",
            "--timeout",
            "60s",
            "--metrics-brief",
            "--oom-avoid",
        ]
    )

    if r.returncode:
        logger.error("perf stat memory stress-ng FAILED")
    else:
        logger.info("perf stat memory stress-ng PASSED")


def test_perf_stat_network_stress_ng(client: SSHClient | None) -> None:
    perf = Perf(client)
    r = perf(
        [
            "stat",
            "-e",
            "net:net_dev_xmit,net:netif_rx,syscalls:sys_enter_sendto,syscalls:sys_enter_recvfrom",
            "-a",
            "--",
            "stress-ng",
            "--sock",
            "3",
            "--timeout",
            "60s",
            "--metrics-brief",
            "--oom-avoid",
        ]
    )

    if r.returncode:
        logger.error("perf stat network stress-ng FAILED")
    else:
        logger.info("perf stat network stress-ng PASSED")


def test_perf_stat_find_syscalls(client: SSHClient | None) -> None:
    perf = Perf(client)
    r = perf(
        [
            "stat",
            "-e",
            "syscalls:sys_enter_newstat,syscalls:sys_enter_newlstat,syscalls:sys_enter_newfstatat,syscalls:sys_enter_openat,context-switches,minor-faults",
            "--",
            "find",
            "/tmp",  # noqa: S108
            "-name",
            "nonexistentfile",
        ]
    )

    if r.returncode:
        logger.error("perf stat find syscalls FAILED")
    else:
        logger.info("perf stat find syscalls PASSED")
