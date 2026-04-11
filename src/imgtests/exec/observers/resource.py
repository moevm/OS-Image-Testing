import logging
from typing import TYPE_CHECKING

from imgtests.exec.exec import common_run_command

if TYPE_CHECKING:
    from imgtests.exec.exec import SSHClient

logger = logging.getLogger(__name__)


def get_total_ram_size(client: SSHClient | None = None) -> int | None:
    """Returns total RAM size in KiB."""
    result = common_run_command(["grep", "MemTotal", "/proc/meminfo"], ssh_client=client)
    if result.returncode:
        logger.error("Finding total RAM size failed.")
        return None
    try:
        return int(result.stdout.split()[1])
    except (IndexError, ValueError):
        logger.exception("Finding total RAM size failed.")
        return None


def get_available_ram_size(client: SSHClient | None = None) -> int | None:
    """Returns available RAM size in KiB."""
    result = common_run_command(["grep", "MemAvailable", "/proc/meminfo"], ssh_client=client)
    if result.returncode:
        logger.error("Finding available RAM size failed.")
        return None
    try:
        return int(result.stdout.split()[1])
    except (IndexError, ValueError):
        logger.exception("Finding available RAM size failed.")
        return None
