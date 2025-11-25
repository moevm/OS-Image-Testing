from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from imgtests.exec.exec import SSHClient

logger = logging.getLogger(__name__)


def _parse_os_release(content: str) -> dict[str, str]:
    """Parse /etc/os-release contents into a dict of key/value pairs."""
    data: dict[str, str] = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def get_os_release(ssh_client: SSHClient) -> dict[str, str]:
    """Return a dict with fields from /etc/os-release on a remote system."""
    result = ssh_client("cat /etc/os-release")
    if result.returncode:
        logger.warning(
            "Failed to read /etc/os-release on remote host '%s': %s",
            ssh_client.hostname,
            result.stderr,
        )
        return {}

    return _parse_os_release(result.stdout)


def get_os_id(ssh_client: SSHClient) -> str | None:
    """Return the distribution ID."""
    data = get_os_release(ssh_client)
    return data.get("ID")
