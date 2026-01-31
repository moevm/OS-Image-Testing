import logging
import shlex
from typing import Final

from imgtests.exec.exec import SSHClient, common_run_command
from imgtests.exec.loaders import StressNg

logger = logging.getLogger(__name__)

_GOOGLE_URL: Final = shlex.quote("http://142.250.185.206/")
_DNS_SERVER: Final = shlex.quote("8.8.8.8")


def test_endurance_network(client: SSHClient | None) -> None:
    stress_ng = StressNg(client)
    result, (metrics, summary) = stress_ng.run(timeout_sec=10, sock=2, sock_ops=2)
    if result.returncode:
        logger.error("NETWORK endurance test FAILED")
        return
    if summary:
        logger.info(summary)
    if metrics:
        logger.info(metrics)

    cmd = (
        "GOOGLE_DNS="
        + _DNS_SERVER
        + " GOOGLE_IP="
        + _GOOGLE_URL
        + " bash ./scripts/network_endurance.sh"
    )
    result = common_run_command(["bash", "-lc", cmd], client)
    if result.returncode:
        logger.error("NETWORK endurance test FAILED")
        return
    logger.info("NETWORK endurance test PASSED")
