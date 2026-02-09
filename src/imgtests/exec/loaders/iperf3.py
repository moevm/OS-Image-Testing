import logging

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import SSHClient

logger = logging.getLogger(__name__)


class Iperf3(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("iperf3", ssh_client)
