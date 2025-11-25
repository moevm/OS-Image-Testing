import shlex
from pathlib import Path

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient

DEFAULT_LTP_RESULTS_DIR = Path("/var/tmp/ltp-results")


class Kirk(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("kirk", ssh_client)
        
    def run(
        self,
        scenario: str,
        shared_dir: str | Path = DEFAULT_LTP_RESULTS_DIR
    ) -> Path | ExecResult:
        """Run an LTP scenario via kirk on a remote host and store results as JSON."""
        if self.ssh_client is None:
            msg = (
                "SSH client is not configured; running LTP via kirk "
                f"for scenario {scenario!r} is not possible."
            )
            return ExecResult(
                cmd="run-ltp",
                stdout="",
                stderr=msg,
                returncode=1,
            )

        shared_dir = Path(shared_dir)
        shared_dir_str = str(shared_dir)

        mkdir_cmd = f"mkdir -p {shlex.quote(shared_dir_str)}"
        mkdir_res = self.ssh_client(mkdir_cmd)
        if mkdir_res.returncode != 0:
            raise RuntimeError(
                "Failed to create shared directory on remote host: "
                f"{shared_dir_str}\n"
                f"STDOUT:\n{mkdir_res.stdout}\n"
                f"STDERR:\n{mkdir_res.stderr}"
            )

        json_path = shared_dir / f"{scenario}.json"

        cmd = ["--run-suite", scenario, "--json-report", str(json_path)]
        res = self(cmd)

        if res.returncode != 0:
            return res

        return json_path
