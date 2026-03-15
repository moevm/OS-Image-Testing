import logging

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient, common_run_command
from imgtests.exec.user_commands import Dd

logger = logging.getLogger(__name__)


class DeviceMapperSetup(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("dmsetup", ssh_client)

    def list_dm_devices(self) -> ExecResult:
        return self(["ls"])

    def create_dm_delay_device(
        self,
        device_name: str = "delay",
        block_name: str = "/dev/loop0",
        r_delay: int = 2000,
        w_delay: int = 2000,
    ) -> bool:
        result = self.list_dm_devices()

        if f"{device_name}1" in result.stdout:
            return True

        sectors = 1048576
        result = self(
            [
                "create",
                f"{device_name}1",
                "--table",
                f'"0 {sectors} {device_name} {block_name} 0 {r_delay} {block_name} 0 {w_delay}"',
            ]
        )
        return result.returncode == 0

    def create_dm_dust_device(
        self, device_name: str = "dust", block_name: str = "/dev/loop0", block_size: int = 512
    ) -> bool:
        result = self.list_dm_devices()

        if f"{device_name}1" in result.stdout:
            return True

        sectors = 1048576
        result = self(
            [
                "create",
                f"{device_name}1",
                "--table",
                f'"0 {sectors} {device_name} {block_name} 0 {block_size}"',
            ]
        )
        return result.returncode == 0

    def add_bad_blocks(self, device_name: str, block_numbers: list[int]) -> None:
        result = self(["message", device_name, 0, "enable"])

        self(["message", device_name, 0, "clearbadblocks"])

        if result.returncode:
            return
        for block_number in block_numbers:
            result = self(["message", device_name, 0, "addbadblock", block_number])
            if result.returncode:
                logger.error("BLOCK NOT ADDED")

    def remove_dm_device(self, device_name: str) -> bool:
        result = self(["remove", device_name])
        return result.returncode == 0


def setup_block_device(
    client: SSHClient | None = None,
    block_name: str = "/dev/loop0",
    block_size: str = "1M",
    block_count: int = 512,
) -> bool:
    dd = Dd(ssh_client=client)
    result = dd(["if=/dev/zero", "of=storage.img", f"bs={block_size}", f"count={block_count}"])
    if result.returncode:
        return False

    result = common_run_command(
        cmd=["losetup", "-a"],
        ssh_client=client,
    )
    if block_name in result.stdout and "storage.img" in result.stdout:
        return True

    result = common_run_command(
        cmd=["losetup", block_name, "storage.img"],
        ssh_client=client,
    )
    if result.returncode:
        return False

    logger.info("Block device setup successful")
    return True
