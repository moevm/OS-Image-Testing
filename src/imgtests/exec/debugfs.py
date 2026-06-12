import logging
from pathlib import Path
from typing import TYPE_CHECKING

from imgtests.exec.exec import ExecResult, SSHClient, common_run_command

if TYPE_CHECKING:
    from imgtests.exec.exec import ExecResult, SSHClient

DEBUGFS_MOUNTPOINT = Path("/sys/kernel/debug")
DEBUG_FS_PATH = "/sys/kernel/debug/"
MAX_FAULT_PROBABILITY = 100

logger = logging.getLogger(__name__)


def ensure_debugfs(ssh_client: SSHClient) -> ExecResult:
    """Ensures that debugfs is created and mounted."""
    debugfs_path = str(DEBUGFS_MOUNTPOINT)
    result = common_run_command(("sudo", "mkdir", "-p", debugfs_path), ssh_client)
    if result.returncode:
        return result
    mount_pattern = f"[[:space:]]{debugfs_path}[[:space:]]debugfs[[:space:]]"
    result = common_run_command(
        ("sudo", "grep", "-qs", mount_pattern, "/proc/mounts"),
        ssh_client,
    )
    if result.returncode == 0 or result.returncode != 1:
        return result
    logger.info("Mounting debugfs to '%s'.", debugfs_path)
    result = common_run_command(
        ("sudo", "mount", "-t", "debugfs", "debugfs", debugfs_path),
        ssh_client,
    )

    if result.returncode:
        logger.info("Unmounting debugfs from '%s'.", debugfs_path)
        common_run_command(("sudo", "umount", debugfs_path), ssh_client)
    return result


def validate_fault_probability(fault_prob: int) -> None:
    """Checks if fault injection probability is in between borders."""
    if not 0 <= fault_prob <= MAX_FAULT_PROBABILITY:
        err_msg = f"fault_probability must be in range 0..{MAX_FAULT_PROBABILITY}."
        raise ValueError(err_msg)


def change_fault_parameters(
    client: SSHClient,
    fault_probability: int,
    fault_interval: int,
) -> ExecResult:
    result = ensure_debugfs(client)
    if result.returncode:
        return result

    result = common_run_command(["ls", DEBUG_FS_PATH], ssh_client=client)
    if result.returncode:
        logger.error("Failed to list debugfs directory.")
        return result

    dirs = [
        i
        for i in result.stdout.splitlines()
        if ("fail" in i or "fault" in i) and i != "fault_around_bytes"
    ]
    if not dirs:
        logger.warning("No fault-injection debugfs entries found under %s", DEBUG_FS_PATH)
        return result

    times = -1 if fault_probability > 0 else 1
    last_result = result
    for directory in dirs:
        dir_path = DEBUG_FS_PATH + directory
        updates = (
            ("interval", fault_interval),
            ("space", 0),
            ("times", times),
            ("probability", fault_probability),
        )

        for parameter, value in updates:
            write_cmd = ["echo", f"{value}", ">", f"{dir_path}/{parameter}"]
            result = common_run_command(write_cmd, ssh_client=client)
            last_result = result
            if result.returncode:
                logger.error(
                    "Failed to update fault-injection parameter %s in %s",
                    parameter,
                    dir_path,
                )
                return result
    return last_result
