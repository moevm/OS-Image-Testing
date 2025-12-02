import logging
import shlex
from pathlib import Path

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient

logger = logging.getLogger(__name__)

DEFAULT_LTP_RESULTS_DIR = Path("/var/tmp/ltp-results")


class Kirk(GenericUtil):
    def __init__(self, ssh_client: SSHClient) -> None:
        super().__init__("kirk", ssh_client)

    def list_suites(
        self,
        ltp_root: str | Path = "/opt/ltp",
    ) -> list[str]:
        """Return a list of available LTP suites."""
        ltp_root_path = Path(ltp_root)
        runtest_dir = ltp_root_path / "runtest"

        cmd = f"ls -1 {shlex.quote(str(runtest_dir))}"
        res = self.ssh_client(cmd)

        if res.returncode != 0:
            logger.error(
                "Failed to list LTP suites in %s\nSTDOUT:\n%s\nSTDERR:\n%s",
                runtest_dir,
                res.stdout,
                res.stderr,
            )
            return []

        return [line.strip() for line in res.stdout.splitlines() if line.strip()]

    def run(
        self,
        scenarios: list[str],
        results_dir: str | Path = DEFAULT_LTP_RESULTS_DIR,
    ) -> tuple[ExecResult, Path | None]:
        """Run an LTP scenario via kirk on a remote host and store results as JSON."""
        results_dir_path = Path(results_dir)

        remote_results_dir = results_dir_path
        mkdir_cmd = f"mkdir -p {shlex.quote(str(remote_results_dir))}"
        mkdir_res = self.ssh_client(mkdir_cmd)
        if mkdir_res.returncode != 0:
            error_msg = (
                f"Failed to create LTP results directory on remote host: {remote_results_dir}"
            )
            log_msg = f"{error_msg}\nSTDOUT:\n{mkdir_res.stdout}\nSTDERR:\n{mkdir_res.stderr}"
            logger.error(log_msg)
            return (
                ExecResult(
                    cmd=mkdir_cmd,
                    stdout=mkdir_res.stdout,
                    stderr=log_msg,
                    returncode=mkdir_res.returncode,
                ),
                None,
            )

        if len(scenarios) == 1:
            report_name = f"{scenarios[0]}.json"
        else:
            suites_str = "_".join(scenarios)
            report_name = f"{suites_str}.json"

        remote_json_path = remote_results_dir / report_name
        cmd = ["--run-suite", *scenarios, "--json-report", str(remote_json_path)]
        res = self(cmd)

        if res.returncode != 0:
            return res, None

        try:
            results_dir_path.mkdir(parents=True, exist_ok=True)
        except OSError:
            logger.exception(
                "Failed to create local directory for LTP results: %s",
                results_dir_path,
            )
            return res, None

        local_json_path = results_dir_path / remote_json_path.name

        download_res = self.ssh_client.download(
            remotepath=remote_json_path,
            localpath=local_json_path,
        )

        if download_res.returncode != 0:
            logger.error(
                "Failed to download LTP results from remote host. STDERR: %s",
                download_res.stderr,
            )
            return res, None

        return res, local_json_path
