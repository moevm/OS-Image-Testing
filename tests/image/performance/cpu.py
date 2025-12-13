import logging
from concurrent.futures import ThreadPoolExecutor

from imgtests.exec.exec import SSHClient
from imgtests.exec.loaders.stress_ng import StressNg

logger = logging.getLogger(__name__)


def run_stress_ng_tests(executor: ThreadPoolExecutor, client: SSHClient | None = None) -> None:
    stress_ng = StressNg(client)
    future = executor.submit(stress_ng.run, timeout_sec=60, cpu=0)
    result = future.result()
    _, metrics = result
    logger.info(metrics)
