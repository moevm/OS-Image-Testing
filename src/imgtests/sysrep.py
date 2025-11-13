from typing import NamedTuple

from imgtests.exec.exec import SSHClient
from imgtests.exec.loaders.fio import Fio
from imgtests.exec.loaders.kirk import Kirk
from imgtests.exec.loaders.perf import Perf
from imgtests.exec.loaders.stress_ng import StressNg
from imgtests.exec.observers.grep import Grep
from imgtests.exec.observers.uname import Uname, UnameInfo


class ToolsVersions(NamedTuple):
    fio_ver: str
    stress_ng_ver: str
    kirk_ver: str
    perf_ver: str


class SystemInfo(NamedTuple):
    uname_info: UnameInfo
    os: str
    os_ver: str
    tools_versions: ToolsVersions


def get_system_info(ssh_client: SSHClient | None = None) -> SystemInfo:
    uname = Uname(ssh_client)
    grep = Grep(ssh_client)
    return SystemInfo(
        uname.info(),
        os=grep(["-Po", r"^NAME=\s*\"\K.+", "/etc/os-release"]).stdout.strip().replace('"', ""),
        os_ver=grep(["-Po", r"^VERSION=\s*\"\K.+", "/etc/os-release"])
        .stdout.strip()
        .replace('"', ""),
        tools_versions=ToolsVersions(
            Fio(ssh_client).version() or "",
            StressNg(ssh_client).version() or "",
            Kirk(ssh_client).version() or "",
            Perf(ssh_client).version() or "",
        ),
    )
