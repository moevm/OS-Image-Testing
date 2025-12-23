import logging
from concurrent.futures import ThreadPoolExecutor

from imgtests.exec.exec import SSHClient
from imgtests.exec.loaders.chaosblade import Chaosblade
from imgtests.exec.loaders.perf import Perf
from imgtests.exec.loaders.stress_ng import StressNg

logger = logging.getLogger(__name__)


def run_stress_ng_tests(executor: ThreadPoolExecutor, client: SSHClient | None = None) -> None:
    stress_ng = StressNg(client)
    future = executor.submit(stress_ng.run, timeout_sec=60, cpu=0)
    result = future.result()
    _, metrics = result
    logger.info(metrics)


def run_chaosblade_test(executor: ThreadPoolExecutor, client: SSHClient | None = None) -> None:
    chaos = Chaosblade(client)
    perf = Perf(client)
    future_chaos = executor.submit(chaos.create_cpu_exp, cpu_percent=70, timeout_sec=15)
    perf_result = perf.stat(
        cmd=[
            "-e",
            "task-clock",
            "-e",
            "cpu-migrations",
            "-e",
            "cpu-clock",
            "--",
            "bash",
            "-c",
            "echo 'scale=2000; 4*a(1)' | bc -l",
        ]
    )
    chaos_result = future_chaos.result()
    logger.info(chaos_result)
    logger.info(perf_result.stderr)
