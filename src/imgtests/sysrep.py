from typing import Any, NamedTuple

from deepdiff import DeepDiff

from imgtests.exec.exec import SSHClient
from imgtests.exec.loaders.fio import Fio
from imgtests.exec.loaders.kirk import Kirk
from imgtests.exec.loaders.perf import Perf
from imgtests.exec.loaders.stress_ng import StressNg
from imgtests.exec.observers.grep import Grep
from imgtests.exec.observers.rpm import RPM
from imgtests.exec.observers.uname import Uname, UnameInfo
from imgtests.exec.observers.zcat import Zcat


class OsInfo(NamedTuple):
    os: str
    os_ver: str


class ToolsVersions(NamedTuple):
    fio_ver: str
    stress_ng_ver: str
    kirk_ver: str
    perf_ver: str


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


def get_system_info(ssh_client: SSHClient | None = None) -> SystemInfo:
    uname = Uname(ssh_client)
    grep = Grep(ssh_client)
    zcat = Zcat(ssh_client)
    rpm = RPM(ssh_client)
    return SystemInfo(
        uname.info(),
        os_info=OsInfo(
            os=grep(["-Po", r"'^NAME=\s*\"\K.+'", "/etc/os-release"])
            .stdout.strip()
            .replace('"', ""),
            os_ver=grep(["-Po", r"'^VERSION=\s*\"\K.+'", "/etc/os-release"])
            .stdout.strip()
            .replace('"', ""),
        ),
        kernel_config=zcat.get_compressed_files_contents(["/proc/config.gz"]),
        package_list=rpm.get_pkglist(),
        tools_versions=ToolsVersions(
            Fio(ssh_client).version() or "",
            StressNg(ssh_client).version() or "",
            Kirk(ssh_client).version() or "",
            Perf(ssh_client).version() or "",
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
