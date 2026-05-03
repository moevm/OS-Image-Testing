import logging

from imgtests.constant import LIB_NAME
from imgtests.exec.exec import ExecResult, SSHClient, pipeline
from imgtests.exec.osinfo import get_os_release
from imgtests.types import Distro

TIMEOUT_RETURN_CODE: int = 124


class SnapshotManager:
    def __init__(self, name: str, client: SSHClient | None) -> None:
        self._client = client
        self._logger = logging.getLogger(f"{LIB_NAME}.{name}")

    def get_snapshots_info(self) -> ExecResult:
        os_id = get_os_release(self._client).id
        if os_id and os_id != Distro.POKY.value:
            commands: list[list[str]] = [
                ["echo", "info", "snapshots"],
                ["nc", "-q", "0", "10.0.2.2", "4444"],
            ]
        else:
            commands: list[list[str]] = [
                ["echo", "info", "snapshots"],
                ["telnet", "10.0.2.2", "4444"],
            ]
        for result in pipeline(cmds=commands, ssh_client=self._client, pass_output=True):
            if result.returncode:
                self._logger.error("Failed to get snapshots info: %s.", result.cmd)
        self._logger.info("RESULT")
        self._logger.info(result.stdout)
        return result

    def switch_to_snapshot(self, snapshot_name: str) -> None:
        self._logger.info("Switching to snapshot %s.", snapshot_name)
        os_id = get_os_release(self._client).id
        if os_id and os_id != Distro.POKY.value:
            commands: list[list[str]] = [
                ["echo", "loadvm", snapshot_name],
                ["nc", "-q", "0", "10.0.2.2", "4444"],
            ]
        else:
            commands: list[list[str]] = [
                ["echo", "loadvm", snapshot_name],
                ["nc", "-c", "10.0.2.2", "4444"],
            ]
        for result in pipeline(
            cmds=commands,
            ssh_client=self._client,
            pass_output=True,
            timeout=60.0,
        ):
            if result.returncode and result.returncode != TIMEOUT_RETURN_CODE:
                self._logger.error(
                    "Failed to switch to snapshot %s: %s.",
                    snapshot_name,
                    result.cmd,
                )
        if not result.returncode or result.returncode == TIMEOUT_RETURN_CODE:
            self._logger.info("Snapshots switched to %s.", snapshot_name)
        self._client.reconnect()

    def create_snapshot(self, snapshot_name: str) -> None:
        self._logger.info("Creating snapshot: %s.", snapshot_name)
        os_id = get_os_release(self._client).id
        if os_id and os_id != Distro.POKY.value:
            commands: list[list[str]] = [
                ["echo", "savevm", snapshot_name],
                ["nc", "-q", "0", "10.0.2.2", "4444"],
            ]
        else:
            commands: list[list[str]] = [
                ["echo", "savevm", snapshot_name],
                ["nc", "-c", "10.0.2.2", "4444"],
            ]
        for result in pipeline(cmds=commands, ssh_client=self._client, pass_output=True):
            if result.returncode:
                self._logger.error("Failed to create snapshot %s: %s.", snapshot_name, result.cmd)
        if not result.returncode:
            self._logger.info("Snapshot created: %s.", snapshot_name)
