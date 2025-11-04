from imgtests.exec.base_util import BaseTestUtil
from imgtests.exec.exec import SSHClient
from imgtests.exec.utils import extract_version


class Kirk(BaseTestUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("kirk", ssh_client)

    def version(self) -> str | None:
        result = self(["--version"])
        if result.returncode:
            return None
        return extract_version(result.stdout.strip())
