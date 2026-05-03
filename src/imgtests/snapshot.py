import logging
from time import sleep

import paramiko
import paramiko.ssh_exception

from imgtests.constant import LIB_NAME
from imgtests.exec.exec import ExecResult, SSHClient, common_run_command
from imgtests.exec.osinfo import get_os_release
from imgtests.types import Distro

TIMEOUT_RETURN_CODE: int = 124


class SnapshotManager:
    def __init__(self, name: str, client: SSHClient | None) -> None:
        self._client = client
        self._logger = logging.getLogger(f"{LIB_NAME}.{name}")

    def run_command(self, command: str) -> ExecResult:
        os_id = get_os_release(self._client).id
        if os_id and os_id != Distro.POKY.value:
            connector = ["nc", "-q", "0", "10.0.2.2", "4444"]
        else:
            connector = ["socat", "-", "TCP:10.0.2.2:4444"]
        return common_run_command(
            connector,
            ssh_client=self._client,
            input_=command + "\n",
            timeout=60.0,
        )

    def get_snapshots_info(self) -> ExecResult:
        result = self.run_command("info snapshots")
        if result.returncode:
            self._logger.error("Failed to get snapshots info: %s.", result.cmd)
        return result

    def reconnect_after_switch(self) -> None:
        wait_sec = 180
        step_sec = 15
        while wait_sec > 0:
            try:
                return self._client.reconnect()
            except paramiko.ssh_exception.SSHException:
                self._logger.info("Waiting remote node to restart vm.")
            sleep(step_sec)
            wait_sec -= step_sec
        return None

    def switch_to_snapshot(self, snapshot_name: str) -> None:
        self._logger.info("Switching to snapshot %s.", snapshot_name)
        result = self.run_command(f"loadvm {snapshot_name}")
        if result.returncode and result.returncode != TIMEOUT_RETURN_CODE:
            self._logger.error(
                "Failed to switch to snapshot %s: %s.",
                snapshot_name,
                result.cmd,
            )
        if not result.returncode or result.returncode == TIMEOUT_RETURN_CODE:
            self._logger.info("Snapshots switched to %s.", snapshot_name)
        self.reconnect_after_switch()

    def create_snapshot(self, snapshot_name: str) -> None:
        self._logger.info("Creating snapshot: %s.", snapshot_name)
        result = self.run_command(f"savevm {snapshot_name}")
        if result.returncode:
            self._logger.error("Failed to create snapshot %s: %s.", snapshot_name, result.cmd)
        else:
            self._logger.info("Snapshot created: %s.", snapshot_name)
