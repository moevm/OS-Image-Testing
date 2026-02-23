import logging
from typing import TYPE_CHECKING

from imgtests.exec.loaders import StressNg

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


logger = logging.getLogger(__name__)

tests = [
    {"cpu": 0, "cpu_method": "matrixprod"},
    {"vm": 0, "vm_bytes": "2G"},
    {"hdd": 0, "hdd_bytes": "2G"},
    {"sock": 2, "netdev": 2, "udp_flood": 2},
    {"syscall": 0},
    {"mq": 4, "pipe": 4, "sem": 4, "shm": 4},
]


def test_general_consecutive_stress_ng(
    executor: ThreadPoolExecutor, client: SSHClient | None
) -> None:
    stress_ng = StressNg(client)

    for params in tests:
        future = executor.submit(stress_ng.run, timeout_sec=60, **params)
        result = future.result()
        _, metrics = result
        logger.info(metrics)


def test_general_parallel_stress_ng(executor: ThreadPoolExecutor, client: SSHClient | None) -> None:
    stress_ng = StressNg(client)
    futures = []

    for params in tests:
        future = executor.submit(stress_ng.run, timeout_sec=60, **params)
        futures.append(future)

    for future in futures:
        result = future.result()
        _, metrics = result
        logger.info(metrics)
