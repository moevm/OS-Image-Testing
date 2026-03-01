from typing import NamedTuple

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient
from imgtests.exec.loaders.fio import PkgMgrMixin
from imgtests.types import Version


class InstalledPackage(NamedTuple):
    name: str
    version: Version


class Pip3(PkgMgrMixin, GenericUtil):
    """Wrapper around the pip3 Python package manager, working over SSH or locally."""

    def __init__(
        self,
        ssh_client: SSHClient | None = None,
    ) -> None:
        super().__init__("pip3", ssh_client)

    def install(self) -> ExecResult:
        if self.path:
            return ExecResult(
                cmd=(), stderr=f"{self.name} already has been installed.", returncode=0
            )
        return self._install_packages(["python3-pip"])

    def freeze(self) -> set[InstalledPackage]:
        result = self(["freeze"])
        if result.returncode:
            return set()
        installed_packages: set[InstalledPackage] = set()
        for line in result.stdout.splitlines():
            try:
                pkg_name, ver = line.split("==", maxsplit=1)
            except ValueError:
                continue
            installed_packages.add(InstalledPackage(pkg_name, Version(ver)))
        return installed_packages
