from typing import TYPE_CHECKING, NamedTuple

from imgtests.exec.base_util import GenericUtil
from imgtests.types import Version

if TYPE_CHECKING:
    from imgtests.exec.exec import SSHClient


class UnameInfo(NamedTuple):
    kernel_name: str
    kernel_release: Version
    kernel_version: str
    machine: str
    hardware_platform: str
    operating_system: str

    def __str__(self) -> str:
        return " ".join(
            [
                self.kernel_name,
                str(self.kernel_release),
                self.kernel_version,
                self.machine,
                self.hardware_platform,
                self.operating_system,
            ],
        )


class Uname(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("uname", ssh_client)

    def kernel_name(self) -> str:
        return self(["--kernel-name"]).stdout.strip()

    def kernel_release(self) -> str:
        return self(["--kernel-release"]).stdout.strip()

    def kernel_version(self) -> str:
        return self(["--kernel-version"]).stdout.strip()

    def machine(self) -> str:
        return self(["--machine"]).stdout.strip()

    def hardware_platform(self) -> str:
        return self(["--hardware-platform"]).stdout.strip()

    def operating_system(self) -> str:
        return self(["--operating-system"]).stdout.strip()

    def info(self) -> UnameInfo:
        return UnameInfo(
            kernel_name=self.kernel_name(),
            kernel_release=Version(self.kernel_release()),
            kernel_version=self.kernel_version(),
            machine=self.machine(),
            hardware_platform=self.hardware_platform(),
            operating_system=self.operating_system(),
        )
