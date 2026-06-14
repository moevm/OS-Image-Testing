import logging
from pathlib import Path
from typing import TYPE_CHECKING, Final

from imgtests.exec.exec import ExecResult, SSHClient, common_run_command

if TYPE_CHECKING:
    from imgtests.exec.exec import ExecResult, SSHClient

DEBUGFS_PATH: Final = Path("/sys/kernel/debug")
MAX_FAULT_PROBABILITY: Final = 100

logger = logging.getLogger(__name__)


def ensure_debugfs(ssh_client: SSHClient | None) -> ExecResult:
    """Ensures that debugfs is created and mounted."""
    result = common_run_command(("sudo", "mkdir", "-p", str(DEBUGFS_PATH)), ssh_client)
    if result.returncode:
        return result
    mount_pattern = f"[[:space:]]{DEBUGFS_PATH}[[:space:]]debugfs[[:space:]]"
    result = common_run_command(
        ("sudo", "grep", "-qs", mount_pattern, "/proc/mounts"),
        ssh_client,
    )
    if result.returncode == 0 or result.returncode != 1:
        return result
    logger.info("Mounting debugfs to '%s'.", str(DEBUGFS_PATH))
    result = common_run_command(
        ("sudo", "mount", "-t", "debugfs", "debugfs", str(DEBUGFS_PATH)),
        ssh_client,
    )

    if result.returncode:
        logger.info("Unmounting debugfs from '%s'.", str(DEBUGFS_PATH))
        common_run_command(("sudo", "umount", str(DEBUGFS_PATH)), ssh_client)
    return result


def validate_fault_probability(fault_prob: int) -> None:
    """Checks if fault injection probability is in between borders."""
    if not 0 <= fault_prob <= MAX_FAULT_PROBABILITY:
        err_msg = f"fault_probability must be in range 0..{MAX_FAULT_PROBABILITY}."
        raise ValueError(err_msg)


def change_fault_parameters(
    client: SSHClient | None,
    fault_probability: int,
    fault_interval: int,
) -> ExecResult:
    result = ensure_debugfs(client)
    if result.returncode:
        return result

    result = common_run_command(["ls", str(DEBUGFS_PATH)], ssh_client=client)
    if result.returncode:
        logger.error("Failed to list debugfs directory.")
        return result

    dirs = [
        dir_name
        for dir_name in result.stdout.splitlines()
        if ("fail" in dir_name or "fault" in dir_name) and dir_name != "fault_around_bytes"
    ]
    if not dirs:
        logger.warning("No fault-injection debugfs entries found under %s", str(DEBUGFS_PATH))
        return result

    # When fault injection is enabled, times should be set to -1, so that it would run infinitely
    # When fault injection is disabled, times set to default 1
    times = -1 if fault_probability > 0 else 1
    last_result = result
    for directory in dirs:
        dir_path = DEBUGFS_PATH / directory
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
