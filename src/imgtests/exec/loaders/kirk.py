import logging
import shlex
from collections.abc import Iterable
from pathlib import Path

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient, common_run_command
from imgtests.exec.osinfo import get_os_release
from imgtests.exec.pkgmgrs.zypper import Zypper
from imgtests.types import Distro

logger = logging.getLogger(__name__)

DEFAULT_LTP_RESULTS_DIR = Path("/var/tmp/ltp-results")  # noqa: S108


class Kirk(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("kirk", ssh_client)

    def install(self) -> ExecResult:
        """Install kirk from the official Git repository and expose it in PATH."""
        if self.path:
            return ExecResult(
                cmd=(), stderr=f"{self.name} already has been installed.", returncode=0
            )

        os_id = get_os_release(self.ssh_client).id
        if os_id and os_id == Distro.OPEN_SUSE_LEAP.value:
            zypper = Zypper(ssh_client=self.ssh_client, use_sudo=True)
            result = zypper.install_packages(["git-core"])
            if result.returncode:
                return result

        script = (
            "set -e; "
            "install_dir=/opt/kirk; "
            'if [ ! -d "$install_dir" ]; then '
            'git clone https://github.com/linux-test-project/kirk.git "$install_dir"; '
            "fi; "
            'chmod +x "$install_dir/kirk"; '
            'ln -sf "$install_dir/kirk" /usr/local/bin/kirk'
        )
        return common_run_command(("sudo", "bash", "-lc", f"'{script}'"), self.ssh_client)

    def list_suites(
        self,
        ltp_root: str | Path = "/opt/ltp",
    ) -> tuple[str, ...]:
        """Return a list of available LTP suites."""
        ltp_root_path = Path(ltp_root)
        runtest_dir = ltp_root_path / "runtest"

        if self.ssh_client is None:
            try:
                return tuple(
                    sorted(entry.name for entry in runtest_dir.iterdir() if entry.is_file())
                )
            except OSError:
                logger.exception("Failed to list LTP suites in local directory %s", runtest_dir)
                return ()

        res = self.ssh_client(("ls", "-1", shlex.quote(str(runtest_dir))))
        if res.returncode:
            logger.error(
                "Failed to list LTP suites in %s\nSTDOUT:\n%s\nSTDERR:\n%s",
                runtest_dir,
                res.stdout,
                res.stderr,
            )
            return ()

        return tuple(line.strip() for line in res.stdout.splitlines() if line.strip())

    def run(  # noqa: PLR0911
        self,
        scenarios: Iterable[str],
        results_dir: str | Path = DEFAULT_LTP_RESULTS_DIR,
    ) -> tuple[ExecResult, Path | None]:
        """Run an LTP scenario via kirk and store results as JSON."""
        results_dir_path = Path(results_dir)
        scenarios_list = list(scenarios)

        if not scenarios_list:
            scenarios_empty_msg = "scenarios must not be empty"
            raise ValueError(scenarios_empty_msg)

        if self.ssh_client is None:
            try:
                results_dir_path.mkdir(parents=True, exist_ok=True)
            except OSError:
                logger.exception(
                    "Failed to create local directory for LTP results: %s", results_dir_path
                )
                return (
                    ExecResult(
                        cmd=("mkdir", "-p", str(results_dir_path)),
                        stdout="",
                        stderr="Failed to create local directory for LTP results",
                        returncode=1,
                    ),
                    None,
                )
            remote_results_dir = results_dir_path
        else:
            remote_results_dir = Path(results_dir)
            mkdir_cmd = ("mkdir", "-p", shlex.quote(str(remote_results_dir)))
            mkdir_res = self.ssh_client(mkdir_cmd)
            if mkdir_res.returncode != 0:
                error_msg = (
                    f"Failed to create LTP results directory on remote host: {remote_results_dir}"
                )
                logger.error(error_msg)
                logger.error(mkdir_res.stderr)
                return (
                    ExecResult(
                        cmd=mkdir_cmd,
                        stdout=mkdir_res.stdout,
                        stderr=f"{error_msg}\nSTDERR:\n{mkdir_res.stderr}",
                        returncode=mkdir_res.returncode,
                    ),
                    None,
                )

        suites_str = "_".join(scenarios_list)
        report_name = f"{suites_str}.json"

        remote_json_path = remote_results_dir / report_name
        res = self(["--run-suite", *scenarios_list, "--json-report", str(remote_json_path)])
        if res.returncode:
            return res, None

        if self.ssh_client is None:
            local_json_path = remote_json_path
            if not local_json_path.exists():
                logger.error("LTP results JSON was not created locally at %s", local_json_path)
                return res, None
            return res, local_json_path

        try:
            results_dir_path.mkdir(parents=True, exist_ok=True)
        except OSError:
            logger.exception(
                "Failed to create local directory for LTP results: %s", results_dir_path
            )
            return res, None

        local_json_path = results_dir_path / remote_json_path.name
        download_res = self.ssh_client.download(
            remotepath=remote_json_path, localpath=local_json_path
        )

        if download_res.returncode:
            logger.error(
                "Failed to download LTP results from remote host. STDERR: %s", download_res.stderr
            )
            return res, None

        return res, local_json_path
