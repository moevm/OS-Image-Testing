from typing import Any, Literal

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient, run_command
from imgtests.exec.pkgmgrs.mixin import PkgMgrMixin
from imgtests.exec.utils import create_opt

IOPattern = Literal[
    "read", "write", "trim", "randread", "randwrite", "randtrim", "readwrite", "randrw", "trimwrite"
]


class Fio(PkgMgrMixin, GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("fio", ssh_client)

    def install(self) -> ExecResult:
        """Install fio via the system package manager."""
        return self._install_packages(["fio"])

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

    def run(  # noqa: PLR0913
        self,
        name: str | None = None,
        loops: int | None = None,
        numjobs: int | None = None,
        filename: str | None = None,
        size: str | None = None,
        readwrite: IOPattern | None = None,
        ioengine: str | None = None,
        **kwargs: dict[str, Any],
    ) -> ExecResult:
        """Runs the fio util with provided options.

        Args:
            name (str | None): Name of the job.
            loops (int | None): Number of iterations of this job.
            numjobs (int | None): Number of fio jobs.
            filename (str | None): Output filename or block device.
            size (str | None): The total size of file I/O for each thread of this job.
            readwrite (IOPattern | None): Type of I/O pattern.
            ioengine (int | None): How the job issues I/O.
            **kwargs (dict[str, Any]): Command arguments in the free form with values.

        Raises:
            ValueError: When invalid parameters provided or repeated.

        Returns:
            ExecResult: Result of the fio work.
        """
        if numjobs is not None and numjobs <= 0:
            err_msg = f"Invalid numjobs '{numjobs}'. Expected more then 0."
            raise ValueError(err_msg)

        return self(
            [
                *create_opt("name", name),
                *create_opt("loops", loops),
                *create_opt("numjobs", numjobs),
                *create_opt("filename", filename),
                *create_opt("size", size),
                *create_opt("readwrite", readwrite),
                *create_opt("output-format", "json"),
                *create_opt("ioengine", ioengine),
            ],
            **kwargs,
        )


class FioPlot(PkgMgrMixin, GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("fio-plot", ssh_client)

    def _ensure_pip3(self) -> ExecResult | None:
        cmd = ["python3", "-m", "pip", "--version"]
        if self.ssh_client is None:
            check = run_command(cmd)
            if check.returncode == 0:
                return None
            return ExecResult(
                cmd=cmd,
                stdout=check.stdout,
                stderr=(
                    "pip3 is not installed locally; please install it manually "
                    "and re-run fio-plot installation."
                ),
                returncode=check.returncode or 1,
            )

        check = self.ssh_client(cmd)
        if check.returncode == 0:
            return None

        return self._install_packages(["python3-pip"])

    def install(self) -> ExecResult:
        pip_result = self._ensure_pip3()
        if pip_result is not None and pip_result.returncode != 0:
            return pip_result

        cmd = ["python3", "-m", "pip", "install", "fio-plot"]
        if self.ssh_client is None:
            return run_command(cmd)

        return self.ssh_client(cmd)
