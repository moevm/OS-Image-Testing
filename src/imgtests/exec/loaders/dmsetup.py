import logging

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient, common_run_command

logger = logging.getLogger(__name__)


class DeviceMapperSetup(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("dmsetup", ssh_client)

    def create_dm_delay_device(self, device_name: str = "delay", read_delay: int = 2000, write_delay: int = 2000) -> ExecResult:
        result = self(["ls"])

        if f"{device_name}1" in result.stdout:
            return
        
        result = self(["create", f"{device_name}1", "--table", "\"0", "1048576", device_name, "/dev/loop0", "0", read_delay, "/dev/loop0", "0", write_delay, "\""])
        if result.returncode:
            return None
        return result
    
    def create_dm_dust_device(self, device_name: str = "dust", block_size: int = 512) -> ExecResult:
        result = self(["ls"])

        if f"{device_name}1" in result.stdout:
            return

        result = self(["create", f"{device_name}1", "--table", "\"0", "1048576", device_name, "/dev/loop0", "0", block_size, "\""])
        if result.returncode:
            return None
        return result
    
    def add_bad_blocks(self, device_name: str, block_numbers: list[int]) -> None:
        result = self(["message", device_name, 0, "enable"])

        self(["message", device_name, 0, "clearbadblocks"])
        
        if result.returncode:
            return None
        for block_number in block_numbers:
            result = self(["message", device_name, 0, "addbadblock", block_number])
            if result.returncode:
                logger.error("BLOCK NOT ADDED")

    def remove_dm_device(self, device_name: str) -> ExecResult:
        result = self(["remove", device_name])
        if result.returncode:
            return None
        return result


def setup_block_device(ssh_client: SSHClient | None = None, block_size: str = "1M", block_count: int = 512) -> None:
    result = common_run_command(
        cmd=["dd", "if=/dev/zero", "of=storage.img", f"bs={block_size}", f"count={block_count}"],
        ssh_client=ssh_client,
    )
    if result.returncode:
        return result

    result = common_run_command(
        cmd=["losetup", "-a"],
        ssh_client=ssh_client,
    )
    if "/dev/loop0" in result.stdout and "storage.img" in result.stdout:
        return

    result = common_run_command(
        cmd=["losetup", "/dev/loop0", "storage.img"],
        ssh_client=ssh_client,
    )
    if result.returncode:
        return result

    logger.info("Block device setup successful")
