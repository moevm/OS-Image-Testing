from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Final, NamedTuple

from imgtests.exec.exec import common_run_command

if TYPE_CHECKING:
    from imgtests.exec.exec import SSHClient

logger = logging.getLogger(__name__)

_OS_RELEASE_PATH: Final[Path] = Path("/etc/os-release")


class OSRelease(NamedTuple):
    """Structured representation of /etc/os-release contents."""

    raw: dict[str, str]
    id: str
    name: str
    version: str
    version_id: str
    pretty_name: str


def get_os_release(ssh_client: SSHClient | None = None) -> OSRelease:
    """Return selected fields and raw mapping from /etc/os-release."""
    data: dict[str, str] = {}

    result = common_run_command(["cat", str(_OS_RELEASE_PATH)], ssh_client)
    if result.returncode:
        logger.error(result.stderr)
    else:
        data = _parse_os_release(result.stdout)
    return OSRelease(
        raw=data,
        id=data.get("ID", ""),
        name=data.get("NAME", ""),
        version=data.get("VERSION", ""),
        version_id=data.get("VERSION_ID", ""),
        pretty_name=data.get("PRETTY_NAME", ""),
    )


def get_os_id(ssh_client: SSHClient | None = None) -> str | None:
    """Return the distribution ID (ID field from /etc/os-release)."""
    return get_os_release(ssh_client).id


def _parse_os_release(content: str) -> dict[str, str]:
    """Parse /etc/os-release contents into a dict."""
    data: dict[str, str] = {}

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        try:
            key, value = line.split("=", 1)
        except ValueError:
            logger.warning(
                "Failed to parse line from os-release: %r",
                raw_line,
            )
            continue

        data[key.strip()] = value.strip().strip('"')

    return data
