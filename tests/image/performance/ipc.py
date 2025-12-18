import logging

from imgtests.exec.exec import SSHClient
from imgtests.exec.loaders.perf import Perf

logger = logging.getLogger(__name__)


def test_sched(client: SSHClient | None) -> None:
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
