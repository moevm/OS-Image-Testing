import logging

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import SSHClient, common_run_command

logger = logging.getLogger(__name__)


class DeviceMapperSetup(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("dmsetup", ssh_client)

    def create_dm_delay_device(
        self, device_name: str = "delay", read_delay: int = 2000, write_delay: int = 2000
    ) -> bool:
        result = self(["ls"])

        if f"{device_name}1" in result.stdout:
            return True

        result = self(
            [
                "create",
                f"{device_name}1",
                "--table",
                f'"0 1048576 {device_name} /dev/loop0 0 {read_delay} /dev/loop0 0 {write_delay}"',
            ]
        )
        return result.returncode == 0

    def create_dm_dust_device(self, device_name: str = "dust", block_size: int = 512) -> bool:
        result = self(["ls"])

        if f"{device_name}1" in result.stdout:
            return True

        result = self(
            [
                "create",
                f"{device_name}1",
                "--table",
                f'"0 1048576 {device_name} /dev/loop0 0 {block_size}"',
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
    ssh_client: SSHClient | None = None, block_size: str = "1M", block_count: int = 512
) -> bool:
    result = common_run_command(
        cmd=["dd", "if=/dev/zero", "of=storage.img", f"bs={block_size}", f"count={block_count}"],
        ssh_client=ssh_client,
    )
    if result.returncode:
        return False

    result = common_run_command(
        cmd=["losetup", "-a"],
        ssh_client=ssh_client,
    )
    if "/dev/loop0" in result.stdout and "storage.img" in result.stdout:
        return True

    result = common_run_command(
        cmd=["losetup", "/dev/loop0", "storage.img"],
        ssh_client=ssh_client,
    )
    if result.returncode:
        return False

    logger.info("Block device setup successful")
    return True
