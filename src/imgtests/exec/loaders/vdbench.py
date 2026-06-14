import logging
from typing import Final

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient, common_run_command
from imgtests.exec.utils import create_opt

logger = logging.getLogger(__name__)

VDBENCH_DIR: Final = "/usr/sbin/vdbench"
CONFIG_FILE: Final = "/root/vdbench-config"
OUTPUT_DIR: Final = "/root/vdbench-output"


class Vdbench(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("vdbench", ssh_client)
        self.path = VDBENCH_DIR + "/vdbench"

    def validate_setup(self) -> None:
        result = common_run_command(
            ["ls", VDBENCH_DIR],
            self.ssh_client,
        )
        if result.returncode:
            err_msg = f"Tool is not found in {VDBENCH_DIR}"
            raise FileNotFoundError(err_msg)

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
        cmd = [
            "echo",
            "-e",
            f"'{configuration}'",
            ">",
            CONFIG_FILE,
        ]

        return common_run_command(cmd, self.ssh_client)

    def run(
        self,
        timeout_sec: int,
        block_size: int = 4096,
        read_percentage: int = 70,
        iorate: int = 1000,
    ) -> tuple[ExecResult, str]:
        """Runs the vdbench.

        Args:
            timeout_sec (int): Execution time of the vdbench in seconds.
            block_size (int): Block size in bytes for IO operations.
            read_percentage (int): Percentage of read operations.
            iorate (int): IO operations per second.
        """
        self.validate_setup()
        self.configure_params(
            timeout_sec=timeout_sec,
            block_size=block_size,
            read_percentage=read_percentage,
            iorate=iorate,
        )

        opts = [
            *create_opt("f", CONFIG_FILE, use_one_dash=True),
            *create_opt("o", OUTPUT_DIR, use_one_dash=True),
        ]
        result = self(opts)
        return result, OUTPUT_DIR
