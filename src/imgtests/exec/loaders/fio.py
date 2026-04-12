from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from imgtests.adapter import JSONAdapter
from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient, common_run_command
from imgtests.exec.pkgmgrs.mixin import PkgMgrMixin
from imgtests.exec.pkgmgrs.pip3 import Pip3
from imgtests.exec.utils import create_opt
from imgtests.types import MetricSample

if TYPE_CHECKING:
    from imgtests.types import Subsystem, Version

IOPattern = Literal[
    "read", "write", "trim", "randread", "randwrite", "randtrim", "readwrite", "randrw", "trimwrite"
]
# fmt: off
IOEngine = Literal[
    "sync", "psync", "vsync", "pvsync", "pvsync2", "io_uring",
    "io_uring_cmd", "libaio", "posixaio", "solarisaio", "windowsaio",
    "mmap", "splice", "sg", "libzbc", "null", "net", "netsplice",
    "cpuio", "rdma", "falloc", "ftruncate", "e4defrag", "rados",
    "rbd", "http", "gfapi", "gfapi_async", "libhdfs", "mtd",
    "dev-dax", "external", "filecreate", "filestat", "filedelete",
    "libpmem", "ime_psync", "ime_psyncv", "ime_aio", "libiscsi",
    "nbd", "libcufio", "dfs", "nfs", "exec", "xnvme", "libblkio",
]
# fmt: on
Direct = Literal[1] | None
FIO_CLAT_PERCENTILES: dict[str, tuple[str, str]] = {
    "50.000000": ("50", "50"),
    "90.000000": ("90", "90"),
    "95.000000": ("95", "95"),
    "99.000000": ("99", "99"),
    "99.900000": ("999", "99.9"),
}


def get_available_bytes(client: SSHClient | None, path: str | Path) -> int | None:
    res = common_run_command(
        ["df", "--output=avail", "--block-size=1", str(path)],
        client,
    )
    if res.returncode:
        return None

    out = (res.stdout or "").strip().splitlines()
    if not out:
        return None

    try:
        return int(out[-1].strip())
    except (ValueError, IndexError):
        return None


class Fio(PkgMgrMixin, GenericUtil):
    DEFAULT_WORKDIR = Path("/var/lib/imgtests-fio")

    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("fio", ssh_client)

    def install(self) -> ExecResult:
        """Install fio via the system package manager."""
        if self.path:
            return ExecResult(
                cmd=(), stderr=f"{self.name} already has been installed.", returncode=0
            )
        return self._install_packages(["fio"])

    def ioengines(self) -> tuple[str, ...] | None:
        result = self(["--enghelp"])
        if result.returncode:
            return None
        lines = result.stdout.strip().split("\n")
        if len(lines) <= 1:
            return None
        # Skip information line
        if ":" in lines[0]:
            lines = lines[1:]
        return tuple(line.strip() for line in lines)

    @property
    def workdir(self) -> Path:
        common_run_command(["mkdir", "-p", str(self.DEFAULT_WORKDIR)], self.ssh_client)
        return self.DEFAULT_WORKDIR

    def default_filename(self, filename: str) -> str:
        return f"{self.workdir}/{filename}"

    def run(  # noqa: PLR0913
        self,
        name: str | None = None,
        loops: int | None = None,
        numjobs: int | None = None,
        filename: Path | None = None,
        size: str | None = None,
        readwrite: IOPattern | None = None,
        ioengine: IOEngine | None = None,
        direct: Direct = None,
        directory: Path | None = None,
        offset: str | None = None,
        offset_increment: str | None = None,
        **kwargs: dict[str, Any],
    ) -> ExecResult:
        """Runs the fio util with provided options.

        Args:
            name (str | None): Name of the job.
            loops (int | None): Number of iterations of this job.
            numjobs (int | None): Number of fio jobs.
            filename (Path | None): Output filename or block device.
            size (str | None): The total size of file I/O for each thread of this job.
            readwrite (IOPattern | None): Type of I/O pattern.
            ioengine (IOEngine| None): How the job issues I/O.
            direct (Direct): Use non-buffered I/O (when set) or not.
            directory (Path | None): Directory for saving test files.
            offset (str | None): Start offset in bytes or percentage of file size.
            offset_increment (str | None): Per-job offset step added to base offset for each thread.
            **kwargs (dict[str, Any]): Command arguments in the free form with values.

        Raises:
            ValueError: When invalid parameters provided or repeated.

        Returns:
            ExecResult: Result of the fio work.
        """
        if numjobs is not None and numjobs <= 0:
            err_msg = f"Invalid numjobs '{numjobs}'. Expected more then 0."
            raise ValueError(err_msg)

        return self(
            [
                *create_opt("name", name),
                *create_opt("loops", loops),
                *create_opt("numjobs", numjobs),
                *create_opt("filename", filename),
                *create_opt("size", size),
                *create_opt("readwrite", readwrite),
                *create_opt("output-format", "json"),
                *create_opt("ioengine", ioengine),
                *create_opt("direct", direct),
                *create_opt("directory", directory),
                *create_opt("offset", offset),
                *create_opt("offset_increment", offset_increment),
            ],
            **kwargs,
        )

    @staticmethod
    def metrics_to_bmf(metrics: dict[str, Any]) -> dict[str, Any]:  # noqa: PLR0912, C901
        result: dict[str, Any] = {}
        for job in metrics.get("jobs", []):
            name = job["jobname"]
            for op in ["read", "write"]:
                if op not in job:
                    continue
                job_res = job[op]
                fio_metrics = {}
                for metric in [
                    "io_bytes",
                    "io_kbytes",
                    "bw_bytes",
                    "bw",
                    "runtime",
                    "total_ios",
                    "iops",
                ]:
                    if metric in job_res:
                        fio_metrics[metric] = {"value": job_res[metric]}
                for metric in ["bw", "iops"]:
                    if (
                        f"{metric}_mean" in job_res
                        and f"{metric}_min" in job_res
                        and f"{metric}_max" in job_res
                    ):
                        fio_metrics[f"{metric}_mean"] = {
                            "value": job_res[f"{metric}_mean"],
                            "lower_value": job_res[f"{metric}_min"],
                            "upper_value": job_res[f"{metric}_max"],
                        }
                for lat in ["slat_ns", "clat_ns", "lat_ns"]:
                    if lat in job_res and all(k in job_res[lat] for k in ["mean", "min", "max"]):
                        fio_metrics[lat] = {
                            "value": job_res[lat]["mean"],
                            "lower_value": job_res[lat]["min"],
                            "upper_value": job_res[lat]["max"],
                        }
                        if fio_metrics:
                            result[f"{name}_{op}"] = fio_metrics
            cpu = {}
            for metric in ["usr_cpu", "sys_cpu", "ctx"]:
                if metric in job:
                    cpu[metric] = {"value": job[metric]}
            if cpu:
                result[f"{name}_cpu"] = cpu
        return result


class FioPlot(PkgMgrMixin, GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("fio-plot", ssh_client)

    def install(self) -> ExecResult:
        pip3 = Pip3(self.ssh_client)
        result = pip3.install()
        if result.returncode:
            return result

        return pip3(["install", "fio-plot"])

    def version(self) -> Version | None:
        pip3 = Pip3(self.ssh_client)
        installed_packages = pip3.freeze()
        for package in installed_packages:
            if package.name == self.name:
                return package.version
        return None


def fio_metrics_to_samples(
    payload: dict[str, Any],
    stage_name: str,
    subsystem: Subsystem,
) -> list[MetricSample]:
    jobs = payload.get("jobs", [])
    if not isinstance(jobs, list):
        return []

    out: list[MetricSample] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue

        for op in ("read", "write", "trim"):
            op_data = job.get(op, {})
            if not isinstance(op_data, dict):
                continue
            out.extend(
                _fio_op_samples(
                    stage_name=stage_name,
                    subsystem=subsystem.value,
                    op=op,
                    op_data=op_data,
                    percentiles=FIO_CLAT_PERCENTILES,
                )
            )

    return out


def _fio_op_samples(
    stage_name: str,
    subsystem: str,
    op: str,
    op_data: dict[str, Any],
    percentiles: dict[str, tuple[str, str]],
) -> list[MetricSample]:
    out: list[MetricSample] = []
    op_label = op.capitalize()

    iops = _safe_float(op_data.get("iops"))
    bw = _safe_float(op_data.get("bw"))
    runtime_ms = _safe_float(op_data.get("runtime"))

    clat = op_data.get("clat_ns") or {}
    clat_mean = _safe_float(clat.get("mean")) if isinstance(clat, dict) else None

    if iops is not None:
        out.append(
            MetricSample(stage_name, subsystem, f"fio.{op}.iops", iops, label=f"{op_label} IOPS")
        )
    if bw is not None:
        out.append(
            MetricSample(
                stage_name,
                subsystem,
                f"fio.{op}.bw_kib_s",
                bw,
                label=f"{op_label} bandwidth, KiB/s",
            )
        )
    if runtime_ms is not None:
        out.append(
            MetricSample(
                stage_name,
                subsystem,
                f"fio.{op}.runtime_ms",
                runtime_ms,
                label=f"{op_label} runtime, ms",
            )
        )
    if clat_mean is not None:
        out.append(
            MetricSample(
                stage_name,
                subsystem,
                f"fio.{op}.clat_mean_ns",
                clat_mean,
                label=f"{op_label} clat mean, ns",
            )
        )

    pct = clat.get("percentile") if isinstance(clat, dict) else None
    if isinstance(pct, dict):
        for key, (metric_suffix, percentile_label) in percentiles.items():
            fv = _safe_float(pct.get(key))
            if fv is not None:
                out.append(
                    MetricSample(
                        stage_name,
                        subsystem,
                        f"fio.{op}.clat_p{metric_suffix}_ns",
                        fv,
                        label=f"{op_label} clat p{percentile_label}, ns",
                    )
                )

    return out


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class FioAdapter(JSONAdapter):
    def __init__(self) -> None:
        self.tool = "fio"

    def split_result(self, raw_result: dict[str, Any], test_index: int = 0) -> dict[str, Any]:
        jobs = raw_result.get("jobs", [])
        job = jobs[test_index]

        metrics = {
            "read": job.get("read", {}),
            "write": job.get("write", {}),
            "trim": job.get("trim", {}),
        }

        job_options = job.get("job options", {})
        test_type = {
            "name": job_options.get("name", ""),
            "size": job_options.get("size", ""),
            "rw": job_options.get("rw", ""),
            "ioengine": job_options.get("ioengine", ""),
            "bs": job_options.get("bs", ""),
        }

        time = {
            "timestamp": raw_result.get("timestamp", 0),
            "time": raw_result.get("time", 0),
            "job_runtime": job.get("job_runtime", 0),
        }

        summary = {
            "jobs_count": len(jobs),
            "failed_jobs": sum(1 for j in jobs if j.get("error", 0) != 0),
        }

        return {
            "test_type": test_type,
            "time": time,
            "metrics": metrics,
            "summary": summary,
        }
