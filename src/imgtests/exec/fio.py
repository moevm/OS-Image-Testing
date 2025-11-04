from imgtests.exec.base_util import BaseTestUtil
from imgtests.exec.exec import ExecResult, SSHClient
from imgtests.exec.utils import create_opt, extract_version


class Fio(BaseTestUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("fio", ssh_client)

    def ioengines(self) -> tuple[str, ...] | None:
        result = self(["--enghelp"])
        if result.returncode:
            return None
        lines = result.stdout.strip().split("\n")
        if len(lines) <= 1:
            return None
        # Skip information line
        if ":" in lines[0]:
            lines = lines[1:]
        return tuple(line.strip() for line in lines)

    def run(
        self,
        numjobs: int | None,
        ioengine: str | None,
    ) -> ExecResult:
        """Runs the fio util with provided options.

        Args:
            numjobs (int | None): Number of fio jobs.
            ioengine (int | None): How the job issues I/O.

        Raises:
            ValueError: When invalid parameters provided.

        Returns:
            ExecResult: Result of the fio work.
        """
        if numjobs is not None and numjobs <= 0:
            err_msg = f"Invalid numjobs '{numjobs}'. Expected more then 0."
            raise ValueError(err_msg)

        return self(
            [
                *create_opt("numjobs", numjobs),
                *create_opt("output-format", "json"),
                *create_opt("ioengine", ioengine),
            ]
        )

    def version(self) -> str | None:
        result = self(["--version"])
        if result.returncode:
            return None
        return extract_version(result.stdout.strip())
