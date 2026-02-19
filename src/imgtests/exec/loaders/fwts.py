import logging
from typing import TYPE_CHECKING

from imgtests.exec.base_util import GenericUtil

if TYPE_CHECKING:
    from imgtests.exec.exec import SSHClient

logger = logging.getLogger(__name__)


class Fwts(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("fwts", ssh_client)
