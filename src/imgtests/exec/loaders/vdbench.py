import logging

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient, common_run_command

logger = logging.getLogger(__name__)

VDBENCH_DIR = "/usr/bin/vdbench"
OUTPUT_DIR = VDBENCH_DIR + "/output"

class Vdbench(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("vdbench", ssh_client)

    def validate_setup(self) -> None:
        result = common_run_command(
            ["ls", VDBENCH_DIR],
            self.ssh_client,
        )
        if result.returncode:
            err_msg = f"Tool is not found in {VDBENCH_DIR}"
            raise FileNotFoundError(err_msg)
    
    def configure_params(self, timeout_sec: int, **kwargs: str | float | bool | None) -> ExecResult:
        block_size = kwargs.get("block_size", 4096)
        read_percentage = kwargs.get("read_percentage", 70)
        iorate = kwargs.get("iorate", 1000)
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
            "vdbench-config"
        ]

        result = common_run_command(cmd, self.ssh_client)
        return result
    
    def run(self, timeout_sec: int, **kwargs: str | float | bool | None) -> tuple[ExecResult, str]:
        self.validate_setup()
        self.configure_params(timeout_sec=timeout_sec, **kwargs)
        result = common_run_command([f"{VDBENCH_DIR}/vdbench", "-f", "vdbench-config"], self.ssh_client)
        return result, OUTPUT_DIR
