import logging

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient

logger = logging.getLogger(__name__)


class Fwts(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("fwts", ssh_client)

    def run(self, add_opts: list[str] | None = None) -> ExecResult:
        if add_opts is None:
            add_opts = []
        return self([*add_opts])
