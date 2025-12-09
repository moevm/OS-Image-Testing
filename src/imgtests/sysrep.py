from typing import NamedTuple

from imgtests.exec.exec import SSHClient
from imgtests.exec.loaders.fio import Fio
from imgtests.exec.loaders.kirk import Kirk
from imgtests.exec.loaders.perf import Perf
from imgtests.exec.loaders.stress_ng import StressNg
from imgtests.exec.observers.uname import Uname, UnameInfo
from imgtests.exec.osinfo import get_os_release


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
    os_release = get_os_release(ssh_client)

    os_name = os_release.name or ""
    os_ver = os_release.raw.get("VERSION") or ""

    return SystemInfo(
        uname.info(),
        os=os_name,
        os_ver=os_ver,
        tools_versions=ToolsVersions(
            Fio(ssh_client).version() or "",
            StressNg(ssh_client).version() or "",
            Kirk(ssh_client).version() or "",
            Perf(ssh_client).version() or "",
        ),
    )
