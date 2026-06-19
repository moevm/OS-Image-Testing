import logging
from pathlib import Path
from typing import Final

from imgtests.constant import LIB_NAME
from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient, common_run_command
from imgtests.exec.utils import create_opt

logger = logging.getLogger(__name__)

VDBENCH_NAME: Final = "vdbench"
VDBENCH_DIR: Final = Path("/usr/sbin") / VDBENCH_NAME


class Vdbench(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__(VDBENCH_NAME, ssh_client)
        self.path = VDBENCH_DIR / VDBENCH_NAME

    def validate_setup(self) -> ExecResult:
        result = common_run_command(["ls", str(self.path)], self.ssh_client)
        if result.returncode:
            return ExecResult(
                cmd=result.cmd,
                stderr=f"Failed to locate '{self.name}'.",
                returncode=1,
            )
        return result

    def configure_params(
        self,
        config_file: Path,
        timeout_sec: int = 60,
        block_size: int = 4096,
        read_percentage: int = 70,
        iorate: int = 1000,
    ) -> ExecResult:
        configuration = (
            f"sd=sd1,lun=storage.img,size=1024m\n"
            f"wd=wd1,sd=sd1,xfersize={block_size},readpct={read_percentage},seekpct=100\n"
            f"rd=run1,wd=wd1,iorate={iorate},elapsed={timeout_sec},interval=1"
        )
        result = self.__provide_folder(config_file.parent)
        if result.returncode:
            return result
        return common_run_command(
            [
                "echo",
                "-e",
                f"'{configuration}'",
                ">",
                str(config_file),
            ],
            self.ssh_client,
        )

    def run(
        self,
        timeout_sec: int,
        block_size: int = 4096,
        read_percentage: int = 70,
        iorate: int = 1000,
    ) -> tuple[ExecResult, Path | None]:
        """Runs the vdbench.

        Args:
            timeout_sec (int): Execution time of the vdbench in seconds.
            block_size (int): Block size in bytes for IO operations.
            read_percentage (int): Percentage of read operations.
            iorate (int): IO operations per second.
        """
        result = self.validate_setup()
        if result.returncode:
            return result, None
        result = common_run_command(["echo", "$HOME"], self.ssh_client)
        home_dir = result.stdout.strip()
        if result.returncode or not home_dir:
            return result, None

        config_file: Final = Path(home_dir) / LIB_NAME / VDBENCH_NAME / f"{VDBENCH_NAME}-config"
        self.configure_params(
            config_file=config_file,
            timeout_sec=timeout_sec,
            block_size=block_size,
            read_percentage=read_percentage,
            iorate=iorate,
        )

        output_dir = Path(home_dir) / LIB_NAME / VDBENCH_NAME / f"{VDBENCH_NAME}-output"
        result = self.__provide_folder(output_dir)
        if result.returncode:
            return result, None
        opts = [
            *create_opt("f", config_file, use_one_dash=True),
            *create_opt("o", output_dir, use_one_dash=True),
        ]
        result = self(opts)
        return result, output_dir

    def __provide_folder(self, folder: Path) -> ExecResult:
        result = common_run_command(["test", "-d", str(folder)], self.ssh_client)
        if result.returncode:
            return common_run_command(["mkdir", "--parents", str(folder)], self.ssh_client)
        return result
