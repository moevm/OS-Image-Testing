from typing import TYPE_CHECKING, Any, NamedTuple

from deepdiff import DeepDiff

from imgtests.exec.loaders import (
    Fio,
    FioPlot,
    Fwts,
    Iperf3,
    Kirk,
    Perf,
    PhoronixTestSuite,
    StressNg,
)
from imgtests.exec.observers.uname import Uname, UnameInfo
from imgtests.exec.observers.zcat import Zcat
from imgtests.exec.osinfo import get_os_release
from imgtests.exec.pkgmgrs.rpm import RPM
from imgtests.types import Version

if TYPE_CHECKING:
    from imgtests.exec.exec import SSHClient


class OsInfo(NamedTuple):
    os: str
    os_ver: Version

    def __str__(self) -> str:
        return f"{self.os} {self.os_ver!s}"


class ToolsVersions(NamedTuple):
    fio_ver: Version
    fio_plot_ver: Version
    fwts_ver: Version
    stress_ng_ver: Version
    kirk_ver: Version
    perf_ver: Version
    pts_ver: Version
    iperf3_ver: Version


class SystemInfo(NamedTuple):
    uname_info: UnameInfo
    os_info: OsInfo
    kernel_config: tuple[str, ...]
    package_list: tuple[str, ...]
    tools_versions: ToolsVersions


class SystemInfoDiff(NamedTuple):
    uname_diff: dict[str, Any]
    os_diff: dict[str, Any]
    tools_diff: dict[str, Any]


def get_system_info(
    ssh_client: SSHClient | None = None,
    rpm_format: str = "'%{NAME} %{VERSION}:%{RELEASE}:%{ARCH}\n'",
) -> SystemInfo:
    uname = Uname(ssh_client)
    zcat = Zcat(ssh_client)
    rpm = RPM(ssh_client)
    os_release = get_os_release(ssh_client)

    os_name = os_release.name
    os_ver = os_release.version or os_release.version_id

    return SystemInfo(
        uname.info(),
        os_info=OsInfo(
            os=os_name,
            os_ver=Version(os_ver),
        ),
        kernel_config=zcat.get_compressed_files_contents(["/proc/config.gz"]),
        package_list=rpm.get_pkglist(rpm_format),
        tools_versions=ToolsVersions(
            Fio(ssh_client).version() or Version(""),
            FioPlot(ssh_client).version() or Version(""),
            Fwts(ssh_client).version() or Version(""),
            StressNg(ssh_client).version() or Version(""),
            Kirk(ssh_client).version() or Version(""),
            Perf(ssh_client).version() or Version(""),
            PhoronixTestSuite(ssh_client).version() or Version(""),
            Iperf3(ssh_client).version() or Version(""),
        ),
    )


def compare_system_infos(sys_info1: SystemInfo, sys_info2: SystemInfo) -> SystemInfoDiff:
    uname_diff = DeepDiff(sys_info1.uname_info, sys_info2.uname_info)
    os_diff = DeepDiff(sys_info1.os_info, sys_info2.os_info)
    tools_diff = DeepDiff(sys_info1.tools_versions, sys_info2.tools_versions)
    return SystemInfoDiff(
        uname_diff,
        os_diff,
        tools_diff,
    )
