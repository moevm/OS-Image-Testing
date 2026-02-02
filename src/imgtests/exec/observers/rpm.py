from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import SSHClient


class RPM(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("rpm", ssh_client)

    def get_pkglist(self, rpm_format: str | None) -> tuple[str, ...]:
        if rpm_format is None:
            # default rpm -qa return format
            rpm_format = "'%{NAME}-%{VERSION}-%{RELEASE}-%{ARCH}\n'"
        return tuple(self([
            "-qa",
            "--queryformat",
            rpm_format
        ]).stdout.strip().split("\n"))
