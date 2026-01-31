import logging
import shlex

from imgtests.exec.exec import ExecResult, SSHClient

logger = logging.getLogger(__name__)

_GOOGLE_URL = "http://142.250.185.206/"
_DNS_SERVER = "8.8.8.8"


def _log_on_fail(title: str, res: ExecResult) -> None:
    if res.returncode == 0:
        return
    if res.stdout:
        logger.info("%s stdout:\n%s", title, res.stdout)
    if res.stderr:
        logger.info("%s stderr:\n%s", title, res.stderr)


def test_endurance_network(client: SSHClient | None) -> None:
    if client is None:
        logger.warning("SSH client is None, skipping")
        return

    dns_q = shlex.quote(_DNS_SERVER)
    url_q = shlex.quote(_GOOGLE_URL)

    cmd = "GOOGLE_DNS=" + dns_q + " GOOGLE_IP=" + url_q + " bash ./scripts/network_endurance.sh"
    res = client(["bash", "-lc", cmd])

    if res.returncode == 0:
        logger.info("NETWORK endurance test PASSED")
    else:
        logger.error("NETWORK endurance test FAILED")

    _log_on_fail("network endurance sh", res)
