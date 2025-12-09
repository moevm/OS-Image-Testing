from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient
from imgtests.exec.osinfo import get_os_id
from imgtests.exec.pkgmgrs.zypper import Zypper


class Kirk(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("kirk", ssh_client)

    def install(self) -> ExecResult:
        """Install kirk from the official Git repository and expose it in PATH."""
        if self.ssh_client is None:
            msg = (
                "SSH client is not configured; automatic installation of "
                f"{self.name!r} is not possible."
            )
            return ExecResult(
                cmd=["install-kirk"],
                stdout="",
                stderr=msg,
                returncode=1,
            )

        os_id = get_os_id(self.ssh_client)

        if os_id and "opensuse" in os_id:
            zypper = Zypper(ssh_client=self.ssh_client, use_sudo=True)
            git_result = zypper.install(["git-core"])
            if git_result.returncode != 0:
                return git_result

        script = (
            "set -e; "
            "install_dir=/opt/kirk; "
            'if [ ! -d "$install_dir" ]; then '
            'git clone https://github.com/linux-test-project/kirk.git "$install_dir"; '
            "fi; "
            'chmod +x "$install_dir/kirk"; '
            'ln -sf "$install_dir/kirk" /usr/local/bin/kirk'
        )

        cmd = ["sudo", "bash", "-lc", f"'{script}'"]
        return self.ssh_client(cmd)
