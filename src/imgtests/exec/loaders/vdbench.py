import logging
from pathlib import Path
from typing import Final

from imgtests.constant import LIB_DATA_DIR
from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient, common_run_command
from imgtests.exec.utils import create_opt

logger = logging.getLogger(__name__)

VDBENCH_NAME: Final = "vdbench"
VDBENCH_DIR: Final = Path("/usr/sbin") / VDBENCH_NAME
CONFIG_FILE: Final = LIB_DATA_DIR / VDBENCH_NAME / f"{VDBENCH_NAME}-config"
OUTPUT_DIR: Final = LIB_DATA_DIR / VDBENCH_NAME / f"{VDBENCH_NAME}-output"


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
        if not CONFIG_FILE.parent.exists():
            CONFIG_FILE.parent.mkdir(parents=True)
        cmd = [
            "echo",
            "-e",
            f"'{configuration}'",
            ">",
            str(CONFIG_FILE),
        ]

        return common_run_command(cmd, self.ssh_client)

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
        self.configure_params(
            timeout_sec=timeout_sec,
            block_size=block_size,
            read_percentage=read_percentage,
            iorate=iorate,
        )

        if not OUTPUT_DIR.exists():
            OUTPUT_DIR.mkdir(parents=True)
        opts = [
            *create_opt("f", CONFIG_FILE, use_one_dash=True),
            *create_opt("o", OUTPUT_DIR, use_one_dash=True),
        ]
        result = self(opts)
        return result, OUTPUT_DIR
