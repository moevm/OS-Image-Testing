import json
import logging
import shlex
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient, common_run_command
from imgtests.exec.osinfo import get_os_release
from imgtests.exec.pkgmgrs.zypper import Zypper
from imgtests.exec.utils import create_opt
from imgtests.results_adapter import JSONAdapter
from imgtests.types import Distro

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = logging.getLogger(__name__)

DEFAULT_LTP_RESULTS_DIR = Path("/var/tmp/ltp-results")  # noqa: S108
DEBUGFS_MOUNTPOINT = Path("/sys/kernel/debug")
MAX_FAULT_INJECTION = 100


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
        """Return a list of available LTP suites.

        Args:
            ltp_root (str | Path): Path to directory with LTP suites.

        Returns:
            tuple[str, ...]: Available LTP suites for kirk.
        """
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

    @staticmethod
    def _validate_fault_injection(fault_injection: int) -> None:
        """Checks if fault injection probability is in between borders."""
        if not 0 <= fault_injection <= MAX_FAULT_INJECTION:
            err_msg = f"fault_injection must be in range 0..{MAX_FAULT_INJECTION}."
            raise ValueError(err_msg)

    def _ensure_debugfs(self) -> ExecResult:
        """Ensures that debugfs is created and mounted."""
        debugfs_path = str(DEBUGFS_MOUNTPOINT)
        result = common_run_command(("sudo", "mkdir", "-p", debugfs_path), self.ssh_client)
        if result.returncode:
            return result
        mount_pattern = f"[[:space:]]{debugfs_path}[[:space:]]debugfs[[:space:]]"
        result = common_run_command(
            ("sudo", "grep", "-qs", mount_pattern, "/proc/mounts"),
            self.ssh_client,
        )
        if result.returncode == 0 or result.returncode != 1:
            return result
        logger.info("Mounting debugfs to '%s'.", debugfs_path)
        result = common_run_command(
            ("sudo", "mount", "-t", "debugfs", "debugfs", debugfs_path),
            self.ssh_client,
        )

        if result.returncode:
            logger.info("Unmounting debugfs from '%s'.", debugfs_path)
            common_run_command(("sudo", "umount", debugfs_path), self.ssh_client)
        return result

    def run(  # noqa: PLR0911
        self,
        scenarios: Iterable[str],
        results_dir: str | Path = DEFAULT_LTP_RESULTS_DIR,
        run_pattern: str | None = None,
        timeout: int | None = None,
        fault_injection: int | None = None,
    ) -> tuple[ExecResult, Path | None]:
        """Run an LTP scenario via kirk and store results as JSON.

        Args:
            scenarios (Iterable[str]): List of suites to be run by kirk.
            results_dir (str | Path): Directory for saving kirk test results.
            run_pattern (str | None): Runs tests from suite, which matches
             the given regex pattern.
            timeout (int | None): Timeout before stopping the suite.
            fault_injection (int | None): Probability of failure, ranges from 0 to 100.

        Returns:
            tuple[ExecResult, Path | None]: Result of kirk test work and result path.
        """
        results_dir_path = Path(results_dir)
        scenarios_list = list(scenarios)

        if not scenarios_list:
            scenarios_empty_msg = "scenarios must not be empty"
            raise ValueError(scenarios_empty_msg)

        if fault_injection is not None:
            self._validate_fault_injection(fault_injection)

            debugfs_res = self._ensure_debugfs()
            if debugfs_res.returncode:
                return debugfs_res, None

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
        timestamp = datetime.now(tz=ZoneInfo("UTC")).strftime("%Y-%m-%d_%H:%M:%S")
        report_name = f"{suites_str}_{timestamp}.json"

        remote_json_path = remote_results_dir / report_name

        cmd = [
            *create_opt("run-pattern", run_pattern),
            *create_opt("suite-timeout", timeout),
            *create_opt("fault-injection", fault_injection),
            "--run-suite",
            *scenarios_list,
            "--json-report",
            str(remote_json_path),
        ]

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

    @staticmethod
    def metrics_to_bmf(metrics: Any) -> dict[str, dict[str, dict[str, Any]]]:
        result: dict[str, dict[str, dict[str, Any]]] = {}
        for test in metrics["results"]:
            test_name = test["test_fqn"]
            test_info = test["test"]

            if not test_name or not test_info:
                continue

            arguments = test_info["arguments"]
            arguments_str = " ".join(arguments) if arguments else ""

            retval = test_info["retval"]
            retval_str = retval[0] if retval else ""

            bmf_data: dict[str, dict[str, Any]] = {
                "status": {"value": test["status"]},
                "command": {"value": test_info["command"]},
                "arguments": {"value": arguments_str},
                "log": {"value": test_info["log"]},
                "retval": {"value": retval_str},
                "duration": {"value": test_info["duration"]},
                "failed": {"value": test_info["failed"]},
                "passed": {"value": test_info["passed"]},
                "broken": {"value": test_info["broken"]},
                "skipped": {"value": test_info["skipped"]},
                "warnings": {"value": test_info["warnings"]},
                "result": {"value": test_info["result"]},
            }

            result[test_name] = bmf_data

        return result

    @staticmethod
    def metrics_to_json(metrics: Path) -> dict[str, Any]:
        raw_metrics = json.loads(metrics.read_text())
        adapter = KirkAdapter()
        return adapter(raw_metrics=raw_metrics)


class KirkAdapter(JSONAdapter):
    def __init__(self) -> None:
        self.tool = "kirk"

    def split_result(
        self,
        raw_metrics: dict[str, Any],
        test_index: int = 0,  # noqa: ARG002
    ) -> dict[str, Any]:
        results = raw_metrics.get("results", [])
        metrics = [
            {
                "test": test.get("test_fqn", ""),
                "status": test.get("status", ""),
                "retval": test.get("test", {}).get("retval", []),
                "duration": test.get("test", {}).get("duration", 0.0),
            }
            for test in results
        ]

        summary = raw_metrics.get("stats", {})
        time = {
            "duration_sec": round(summary.get("runtime", 0.0), 2),
        }
        summary = self.drop_fields(summary, ["runtime"])

        return {
            "test_type": {},
            "time": time,
            "metrics": metrics,
            "summary": summary,
        }
