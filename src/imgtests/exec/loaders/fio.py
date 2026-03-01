from typing import TYPE_CHECKING, Any, Literal

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient
from imgtests.exec.pkgmgrs.mixin import PkgMgrMixin
from imgtests.exec.pkgmgrs.pip3 import Pip3
from imgtests.exec.utils import create_opt

if TYPE_CHECKING:
    from pathlib import Path

    from imgtests.types import Version

IOPattern = Literal[
    "read", "write", "trim", "randread", "randwrite", "randtrim", "readwrite", "randrw", "trimwrite"
]
# fmt: off
IOEngine = Literal[
    "sync", "psync", "vsync", "pvsync", "pvsync2", "io_uring",
    "io_uring_cmd", "libaio", "posixaio", "solarisaio", "windowsaio",
    "mmap", "splice", "sg", "libzbc", "null", "net", "netsplice",
    "cpuio", "rdma", "falloc", "ftruncate", "e4defrag", "rados",
    "rbd", "http", "gfapi", "gfapi_async", "libhdfs", "mtd",
    "dev-dax", "external", "filecreate", "filestat", "filedelete",
    "libpmem", "ime_psync", "ime_psyncv", "ime_aio", "libiscsi",
    "nbd", "libcufio", "dfs", "nfs", "exec", "xnvme", "libblkio",
]
# fmt: on
Direct = Literal[1] | None


class Fio(PkgMgrMixin, GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("fio", ssh_client)

    def install(self) -> ExecResult:
        """Install fio via the system package manager."""
        if self.path:
            return ExecResult(
                cmd=(), stderr=f"{self.name} already has been installed.", returncode=0
            )
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
        ioengine: IOEngine | None = None,
        direct: Direct = None,
        directory: Path | None = None,
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
            ioengine (IOEngine| None): How the job issues I/O.
            direct (Direct): Use non-buffered I/O (when set) or not.
            directory (Path | None): Directory for saving test files.
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
                *create_opt("direct", direct),
                *create_opt("directory", directory),
            ],
            **kwargs,
        )


class FioPlot(PkgMgrMixin, GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("fio-plot", ssh_client)

    def install(self) -> ExecResult:
        pip3 = Pip3(self.ssh_client)
        result = pip3.install()
        if result.returncode:
            return result

        return pip3(["install", "fio-plot"])

    def version(self) -> Version | None:
        pip3 = Pip3(self.ssh_client)
        installed_packages = pip3.freeze()
        for package in installed_packages:
            if package.name == self.name:
                return package.version
        return None
