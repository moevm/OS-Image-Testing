import logging
import shlex
from collections.abc import Iterable
from pathlib import Path

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient

logger = logging.getLogger(__name__)

DEFAULT_LTP_RESULTS_DIR = Path("/var/tmp/ltp-results")  # noqa: S108


class Kirk(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("kirk", ssh_client)

    def list_suites(
        self,
        ltp_root: str | Path = "/opt/ltp",
    ) -> list[str]:
        """Return a list of available LTP suites."""
        ltp_root_path = Path(ltp_root)
        runtest_dir = ltp_root_path / "runtest"

        if self.ssh_client is None:
            try:
                return sorted(entry.name for entry in runtest_dir.iterdir() if entry.is_file())
            except OSError:
                logger.exception("Failed to list LTP suites in local directory %s", runtest_dir)
                return []

        cmd = f"ls -1 {shlex.quote(str(runtest_dir))}"
        res = self.ssh_client(cmd)

        if res.returncode:
            logger.error(
                "Failed to list LTP suites in %s\nSTDOUT:\n%s\nSTDERR:\n%s",
                runtest_dir,
                res.stdout,
                res.stderr,
            )
            return []

        return [line.strip() for line in res.stdout.splitlines() if line.strip()]

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
                        cmd=f"mkdir -p {results_dir_path}",
                        stdout="",
                        stderr="Failed to create local directory for LTP results",
                        returncode=1,
                    ),
                    None,
                )
            remote_results_dir = results_dir_path
        else:
            remote_results_dir = Path(results_dir)
            mkdir_cmd = f"mkdir -p {shlex.quote(str(remote_results_dir))}"
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
        cmd = ["--run-suite", *scenarios_list, "--json-report", str(remote_json_path)]
        res = self(cmd)

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
