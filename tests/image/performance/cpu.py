import logging
from typing import TYPE_CHECKING

from imgtests.exec.loaders import Chaosblade, StressNg

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


logger = logging.getLogger(__name__)


def test_stress_ng_cpu(executor: ThreadPoolExecutor, client: SSHClient | None) -> None:
    stress_ng = StressNg(client)
    future = executor.submit(stress_ng.run, timeout_sec=60, cpu=0)
    result = future.result()
    _, metrics = result
    logger.info(metrics)


def test_chaosblade_cpu(executor: ThreadPoolExecutor, client: SSHClient | None) -> None:
    chaos = Chaosblade(client)
    future = executor.submit(chaos.create_cpu_exp, cpu_percent=70, timeout_sec=10)
    _, chaos_result = future.result()
    logger.info(chaos_result)
