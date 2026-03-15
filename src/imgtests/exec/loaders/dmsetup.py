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

    def create_dm_delay_device(  # noqa: PLR0913
        self,
        device_name: str = "delay1",
        target_type: str = "delay",
        start: int = 0,
        sectors: int = 1048576,
        block_path: str = "/dev/loop0",
        read_offset: int = 0,
        read_delay: int = 2000,
        write_offset: int = 0,
        write_delay: int = 2000,
    ) -> ExecResult:
        result = self.list_dm_devices()
        if device_name in result.stdout:
            return result

        return self(
            [
                "create",
                device_name,
                "--table",
                (
                    f'"{start} {sectors} {target_type} '
                    f"{block_path} {read_offset} {read_delay} "
                    f'{block_path} {write_offset} {write_delay}"'
                ),
            ]
        )

    def create_dm_dust_device(  # noqa: PLR0913
        self,
        device_name: str = "dust1",
        target_type: str = "dust",
        start: int = 0,
        sectors: int = 1048576,
        block_path: str = "/dev/loop0",
        offset: int = 0,
        block_size: int = 512,
    ) -> ExecResult:
        result = self.list_dm_devices()
        if device_name in result.stdout:
            return result

        return self(
            [
                "create",
                f"{device_name}",
                "--table",
                (f'"{start} {sectors} {target_type} {block_path} {offset} {block_size}"'),
            ]
        )

    def add_bad_blocks(self, device_name: str, block_numbers: list[int]) -> ExecResult | None:
        result = self(["message", device_name, 0, "enable"])
        if result.returncode:
            return result

        self(["message", device_name, 0, "clearbadblocks"])

        for block_number in block_numbers:
            result = self(["message", device_name, 0, "addbadblock", block_number])
            if result.returncode:
                logger.error("BLOCK NOT ADDED")
        return None

    def remove_dm_device(self, device_name: str) -> ExecResult:
        return self(["remove", device_name])


def setup_block_device(  # noqa: PLR0913
    client: SSHClient | None = None,
    data_source: str = "/dev/zero",
    storage_name: str = "storage.img",
    block_name: str = "/dev/loop0",
    block_size: str = "1M",
    block_count: int = 512,
) -> ExecResult | None:
    dd = Dd(ssh_client=client)
    result = dd(
        [f"if={data_source}", f"of={storage_name}", f"bs={block_size}", f"count={block_count}"]
    )
    if result.returncode:
        return result

    result = common_run_command(
        cmd=["losetup", "-a"],
        ssh_client=client,
    )
    if block_name in result.stdout and storage_name in result.stdout:
        return None

    result = common_run_command(
        cmd=["losetup", block_name, storage_name],
        ssh_client=client,
    )
    if result.returncode:
        return result

    logger.info("Block device setup successful")

    return None
