from imgtests.exec.base_util import BaseTestUtil
from imgtests.exec.exec import ExecResult, SSHClient
from imgtests.exec.utils import extract_version


class Perf(BaseTestUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("perf", ssh_client)

    def stat(self, cmd: list[str]) -> ExecResult:
        return self(["stat", "--json", *cmd])

    def bench(self, cmd: list[str]) -> ExecResult:
        return self(["bench", *cmd])

    def version(self) -> str | None:
        result = self(["--version"])
        if result.returncode:
            return None
        return extract_version(result.stdout.strip())
