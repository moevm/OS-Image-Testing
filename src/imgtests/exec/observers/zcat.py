from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import SSHClient

class Zcat(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("zcat", ssh_client)

    def get_kernel_config(self) -> list[str]:
        return self(["/proc/config.gz", "|", "grep", "-v", "-e", "'^#'", "-e", "'^$'"]).stdout.strip().split('\n')
