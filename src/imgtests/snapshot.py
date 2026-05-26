import logging
from time import sleep

import paramiko
import paramiko.ssh_exception
from pydantic import Field
from pydantic_settings import BaseSettings

from imgtests.constant import LIB_NAME
from imgtests.exec.exec import ExecResult, ExecTimeoutExpiredError, SSHClient, common_run_command
from imgtests.exec.osinfo import get_os_release
from imgtests.types import Distro


class QemuMonitorCreds(BaseSettings):
    host: str = Field(validation_alias="QEMU_MONITOR_ADDRESS")
    port: int = Field(validation_alias="QEMU_MONITOR_PORT", ge=0, le=65535)


class SnapshotManager:
    def __init__(self, name: str, client: SSHClient) -> None:
        self._client = client
        self._logger = logging.getLogger(f"{LIB_NAME}.{name}")
        self.__snapshot_loaded = False

    @property
    def snapshot_loaded(self) -> bool:
        return self.__snapshot_loaded

    def run_command(self, command: str) -> ExecResult:
        qemu_monitor_creds = QemuMonitorCreds()
        os_id = get_os_release(self._client).id
        if os_id and os_id != Distro.POKY.value:
            connector = ["nc", "-q", "0", qemu_monitor_creds.host, str(qemu_monitor_creds.port)]
        else:
            connector = ["socat", "-", f"TCP:{qemu_monitor_creds.host}:{qemu_monitor_creds.port}"]
        return common_run_command(
            connector,
            ssh_client=self._client,
            input_=command + "\n",
            timeout=60.0,
        )

    def get_snapshots_info(self) -> ExecResult:
        return self.run_command("info snapshots")

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
        try:
            result = self.run_command(f"loadvm {snapshot_name}")
            if result.returncode:
                self._logger.error(
                    "Failed to switch to snapshot %s: %s.",
                    snapshot_name,
                    result.cmd,
                )
        except ExecTimeoutExpiredError:
            self._logger.info("Snapshots switched to %s.", snapshot_name)
            self.__snapshot_loaded = True
        self.reconnect_after_switch()

    def create_snapshot(self, snapshot_name: str) -> None:
        self._logger.info("Creating snapshot: %s.", snapshot_name)
        result = self.run_command(f"savevm {snapshot_name}")
        if not result.returncode:
            self._logger.info("Snapshot created: %s.", snapshot_name)
            self.__snapshot_loaded = False
