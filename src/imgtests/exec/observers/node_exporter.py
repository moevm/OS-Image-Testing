from imgtests.exec.exec import ExecResult, SSHClient, common_run_command
from imgtests.exec.osinfo import get_os_release
from imgtests.exec.pkgmgrs.zypper import Zypper
from imgtests.exec.user_commands import SystemService
from imgtests.types import Distro


class NodeExporter(SystemService):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("node_exporter", ssh_client)

    def install(self, collect_flags: list[str] | None = None) -> ExecResult:
        # install package itself
        version = "1.10.2"
        arch = "linux-amd64"
        pkg = "node_exporter"
        install_link = f"https://github.com/prometheus/{self.name}/releases/download/v{version}/{self.name}-{version}.{arch}.tar.gz"

        os_id = get_os_release(self.ssh_client).id
        if os_id and os_id == Distro.OPEN_SUSE_LEAP.value:
            zypper = Zypper(ssh_client=self.ssh_client, use_sudo=True)
            deps_result = zypper.install_packages(["wget", "tar"])
            if deps_result.returncode:
                return deps_result

        install_script = (
            "set -e; "
            f"wget {install_link}; "
            f"tar -xzf {pkg}-{version}.{arch}.tar.gz; "
            f"cd {pkg}-{version}.{arch}; "
            f"cp {pkg} /usr/local/bin/; "
            f"chmod 755 /usr/local/bin/{pkg}; "
            "cd .. "
        )

        install_res = common_run_command(
            ("sudo", "bash", "-lc", f"'{install_script}'"), self.ssh_client
        )
        if install_res.returncode:
            return install_res

        # create daemon if don't exist
        no_daemon_code = 4
        if self.check_exporter().returncode == no_daemon_code:
            if collect_flags is None:
                collect_flags = []

            # systemd daemon conf
            service_text = [
                "[Unit]",
                "Description=Node Exporter",
                "After=network.target",
                "",
                "[Service]",
                "User=nodeuser",
                "Group=nodeuser",
                "Type=simple",
                "ExecStart=/usr/local/bin/node_exporter" + " ".join(collect_flags),
                "",
                "[Install]",
                "WantedBy=multi-user.target",
            ]
            for line in service_text:
                serv_res = common_run_command(
                    ["sudo", "echo", line, " >> ", "node_exporter.service"], self.ssh_client
                )
                if serv_res.returncode:
                    return serv_res

            # create service
            systemd_script = (
                "mv node_exporter.service /etc/systemd/system/; "
                "useradd --no-create-home --shell /bin/false nodeuser; "
                "groupadd nodeuser; "
                f"chown nodeuser:nodeuser /usr/local/bin/{pkg}; "
                "systemctl daemon-reload; "
                f"systemctl disable {pkg}"
            )
            return common_run_command(
                ("sudo", "bash", "-lc", f"'{systemd_script}'"), self.ssh_client
            )

        return install_res
