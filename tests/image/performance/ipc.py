import logging
from concurrent.futures import ThreadPoolExecutor

from imgtests.exec.exec import SSHClient
from imgtests.exec.loaders import Perf

logger = logging.getLogger(__name__)


def test_sched(_: ThreadPoolExecutor, client: SSHClient | None) -> None:
    perf = Perf(client)
    for benchmark, args in zip(
        ["messaging", "messaging", "pipe"], [[], ["--thread"], []], strict=True
    ):
        result = perf.bench("sched", benchmark, args)
        logger.info(
            "Total time: %s. For the benchmark '%s' with args %s.",
            result.stdout,
            benchmark,
            str(args),
        )
