from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import SSHClient

class Zcat(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("zcat", ssh_client)

    def get_compressed_files_contents(self, files: list[str]) -> tuple[str, ...]:
        return tuple(self(files).stdout.strip().split('\n'))
