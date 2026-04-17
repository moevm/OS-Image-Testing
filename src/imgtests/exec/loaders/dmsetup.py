import logging

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient, common_run_command
from imgtests.exec.user_commands import Dd

logger = logging.getLogger(__name__)


class DeviceMapperSetup(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("dmsetup", ssh_client)

    def list_dm_devices(self) -> ExecResult:
        """Returns the list of created device-mapper devices."""
        return self(["ls"])

    def create_dm_delay_device(  # noqa: PLR0913
        self,
        device_name: str = "delay1",
        start: int = 0,
        sectors: int = 1048576,
        block_path: str = "/dev/loop0",
        read_offset: int = 0,
        read_delay: int = 2000,
        write_offset: int = 0,
        write_delay: int = 2000,
    ) -> ExecResult:
        """Creates the dm-delay device.

        Args:
            device_name (str): The name of the created dm-delay device.
            start (int): Starting sector for create operation.
            sectors (int): The amount of used sectors (512-byte each). Counted by dividing
              total given memory by amount of blocks.
            block_path (str): The path to the underlying block device for handling I/O.
            read_offset (int): The starting sector on the read device.
            read_delay (int): The delay in milliseconds to apply to every read request.
            write_offset (int): The starting sector on the write device.
            write_delay (int): The delay in milliseconds to apply to every write request.

        Returns:
            ExecResult: Result of dmsetup ls or create operation.
        """
        result = self.list_dm_devices()
        if device_name in result.stdout:
            return result

        target_type = "delay"
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
            ],
        )

    def create_dm_dust_device(  # noqa: PLR0913
        self,
        device_name: str = "dust1",
        start: int = 0,
        sectors: int = 1048576,
        block_path: str = "/dev/loop0",
        offset: int = 0,
        block_size: int = 512,
    ) -> ExecResult:
        """Creates the dm-dust device.

        Args:
            device_name (str): The name of the created dm-dust device.
            start (int): Starting sector for create operation.
            sectors (int): Amount of used sectors (512-byte each). Counted by dividing total
              given memory by amount of blocks.
            block_path (str): The path to the underlying block device for handling I/O.
            offset (int): The starting sector on block device.
            block_size (int): The block size of block device.

        Returns:
            ExecResult: Result of dmsetup ls or create operation.
        """
        result = self.list_dm_devices()
        if device_name in result.stdout:
            return result

        target_type = "dust"
        return self(
            [
                "create",
                f"{device_name}",
                "--table",
                (f'"{start} {sectors} {target_type} {block_path} {offset} {block_size}"'),
            ],
        )

    def add_bad_blocks(self, device_name: str, block_numbers: list[int]) -> ExecResult:
        """Adds invalid blocks to given device.

        Args:
            device_name (str): The name of the dm device.
            block_numbers (list[int]): The list of block ids to be corrupted.

        Returns:
            ExecResult | None: Result in case of error and None otherwise.
        """
        for cmd in (
            ["message", device_name, "0", "enable"],
            ["message", device_name, "0", "clearbadblocks"],
        ):
            result = self(cmd)
            if result.returncode:
                return result

        for block_number in block_numbers:
            result = self(["message", device_name, "0", "addbadblock", str(block_number)])
            if result.returncode:
                logger.error("Failed to add block %s.", block_number)
                return result
        return result

    def remove_dm_device(self, device_name: str) -> ExecResult:
        """Removes given dm device."""
        return self(["remove", "--deferred", device_name])


def setup_block_device(  # noqa: PLR0913
    client: SSHClient | None = None,
    data_source: str = "/dev/zero",
    storage_name: str = "storage.img",
    block_name: str = "/dev/loop0",
    block_size: str = "1M",
    block_count: int = 512,
) -> ExecResult | None:
    """Setups the block device for device-mapper.

    Args:
        client (SSHClient | None): The active ssh client.
        data_source (str): The name of the device serving as data source for the storage.
        storage_name (str): The name of the created storage serves as a virtual storage.
        block_name (str): The name of the block device, which will be connected with
          storage device.
        block_size (str): The size of each block.
        block_count (int): The amount of blocks created.

    Returns:
        ExecResult | None: Result in case of error and None otherwise.
    """
    dd = Dd(ssh_client=client)
    result = dd(
        [f"if={data_source}", f"of={storage_name}", f"bs={block_size}", f"count={block_count}"],
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
