import logging
from typing import TYPE_CHECKING

from imgtests.exec.base_util import GenericUtil

if TYPE_CHECKING:
    from imgtests.exec.exec import ExecResult, SSHClient

logger = logging.getLogger(__name__)


class SystemdDetectVirt(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("systemd-detect-virt", ssh_client)

    def __call__(self) -> tuple[ExecResult, str | None]:
        result = super().__call__()
        if result.returncode:
            return result, None
        virt_type = result.stdout.strip()
        if virt_type.lower() == "none":
            return result, None
        return result, virt_type
