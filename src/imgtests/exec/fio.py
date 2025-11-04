from imgtests.exec.base_util import BaseTestUtil
from imgtests.exec.exec import ExecResult, SSHClient
from imgtests.exec.utils import extract_version


class Fio(BaseTestUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("fio", ssh_client)

    def __call__(self, cmd: list[str] | None = None) -> ExecResult:
        return super().__call__(cmd)

    def version(self) -> str | None:
        result = self(["--version"])
        if result.returncode:
            return None
        return extract_version(result.stdout.strip())
