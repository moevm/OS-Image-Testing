from __future__ import annotations

import logging
import os
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import product
from pathlib import Path
from typing import TYPE_CHECKING, Any

from imgtests.exec.loaders.fio import Fio, FioPlot, IOPattern
from imgtests.exec.user_commands import MkDir, Rm
from imgtests.suites.duration import EIGHT_HOURS_SEC, HOUR_SEC, TEN_MIN_SEC, TWO_MIN_SEC

if TYPE_CHECKING:
    from imgtests.exec.exec import SSHClient

logger = logging.getLogger(__name__)

_DIFF_GUARD_MAX = 1_000_000
_DEFAULT_TMP_ROOT = Path(tempfile.gettempdir()) / "imgtests-fio"


@dataclass(frozen=True)
class FioWorkload:
    name: str
    rw: IOPattern
    bs: str
    weight: float


@dataclass(frozen=True)
class FioGrid:
    iodepths: tuple[int, ...]
    numjobs: tuple[int, ...]


@dataclass(frozen=True)
class FioTiming:
    grid: FioGrid
    min_runtime_sec: int
    log_avg_msec: int
    ramp_time_sec: int


@dataclass(frozen=True)
class FioCase:
    workload: FioWorkload
    iodepth: int
    numjobs: int
    runtime_sec: int
    out_dir: Path


@dataclass(frozen=True)
class FioSuiteConfig:
    suite: str
    duration_sec: int
    results_dir: Path
    workloads: tuple[FioWorkload, ...]
    size: str = "100MB"
    direct: int = 1
    ioengine: str = "libaio"


class FioSuite:
    def __init__(self, client: SSHClient | None, cfg: FioSuiteConfig) -> None:
        self.client = client
        self.cfg = cfg

    def run(self) -> Path:
        if self.cfg.duration_sec <= 0:
            err_msg = f"duration_sec must be > 0, got {self.cfg.duration_sec}"
            raise ValueError(err_msg)

        fio = Fio(self.client)
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%SZ")
        suite_root = _DEFAULT_TMP_ROOT / f"{self.cfg.suite}-{stamp}"
        suite_tgz = _DEFAULT_TMP_ROOT / f"{self.cfg.suite}-{stamp}.tgz"
        testfiles_dir = suite_root / "testfiles"

        mkdir = MkDir(self.client)
        mkdir(["--parents", suite_root, testfiles_dir])
        workloads = list(self.cfg.workloads)
        timing = _normalize_timing(
            duration_sec=self.cfg.duration_sec,
            workloads_count=len(workloads),
            timing=_timing(self.cfg.duration_sec),
        )
        cases = _plan_cases(
            duration_sec=self.cfg.duration_sec,
            workloads=workloads,
            timing=timing,
            suite_root=suite_root,
        )

        logger.info(
            "fio suite=%s duration=%ss cases=%d iodepth=%s numjobs=%s",
            self.cfg.suite,
            self.cfg.duration_sec,
            len(cases),
            timing.grid.iodepths,
            timing.grid.numjobs,
        )

        for case in cases:
            mkdir(["--parents", case.out_dir])
            prefix = f"{case.workload.rw}-iodepth-{case.iodepth}-numjobs-{case.numjobs}"
            base = case.out_dir / prefix
            out_json = case.out_dir / f"{prefix}.json"

            extra: dict[str, Any] = {
                "directory": testfiles_dir,
                "direct": self.cfg.direct,
                "bs": case.workload.bs,
                "iodepth": case.iodepth,
                "group_reporting": True,
                "time_based": True,
                "runtime": case.runtime_sec,
                "unlink": 1,
                "log_avg_msec": timing.log_avg_msec,
                "write_bw_log": base,
                "write_iops_log": base,
                "write_lat_log": base,
                "output": out_json,
                "eta": "never",
            }
            if timing.ramp_time_sec > 0:
                extra["ramp_time"] = timing.ramp_time_sec

            res = fio.run(
                name=case.workload.name,
                numjobs=case.numjobs,
                size=self.cfg.size,
                readwrite=case.workload.rw,
                ioengine=self.cfg.ioengine,
                **extra,
            )
            if res.returncode:
                err_msg = res.stderr or res.stdout or "fio failed"
                raise RuntimeError(err_msg)

        if self.client:
            _remote_tar(self.client, suite_root, suite_tgz)
            self.cfg.results_dir.mkdir(parents=True, exist_ok=True)
            local_tgz = self.cfg.results_dir / suite_tgz.name
            dl = self.client.download(suite_tgz, local_tgz)
            rm = Rm(self.client)
            rm(["-rf", suite_root, suite_tgz])
            if dl.returncode:
                err_msg = dl.stderr or dl.stdout or "download failed"
                raise RuntimeError(err_msg)
            _local_extract(local_tgz, self.cfg.results_dir)
            local_suite_root = self.cfg.results_dir / f"{self.cfg.suite}-{stamp}"
        else:
            local_suite_root = suite_root
        self._plot(local_suite_root, stamp)
        logger.info("fio done: %s", local_suite_root)
        return local_suite_root

    def _plot(self, local_suite_root: Path, stamp: str) -> None:
        fio_plot = FioPlot()

        for rw_dir in sorted(local_suite_root.iterdir()):
            if not rw_dir.is_dir():
                continue

            rw = rw_dir.name
            for bs_dir in sorted(rw_dir.iterdir()):
                if not bs_dir.is_dir():
                    continue

                title = f"{self.cfg.suite} fio {rw} {bs_dir.name} ({stamp})"
                _run_fio_plot(fio_plot, bs_dir, rw=rw, title=title)


def _timing(duration_sec: int) -> FioTiming:
    if duration_sec <= TWO_MIN_SEC:
        return FioTiming(FioGrid((1,), (1,)), 5, 1000, 0)
    if duration_sec <= TEN_MIN_SEC:
        return FioTiming(FioGrid((1, 4, 16), (1, 2)), 10, 1000, 0)
    if duration_sec <= HOUR_SEC:
        return FioTiming(FioGrid((1, 2, 4, 8, 16, 32), (1, 2, 4)), 20, 2000, 5)
    if duration_sec <= EIGHT_HOURS_SEC:
        return FioTiming(FioGrid((1, 2, 4, 8, 16, 32), (1, 2, 4, 8)), 45, 5000, 10)
    return FioTiming(FioGrid((1, 2, 4, 8, 16, 32), (1, 2, 4, 8)), 60, 5000, 15)


def _shrink_grid(duration_sec: int, workloads_count: int, min_runtime_sec: int) -> FioGrid:
    iodepth_candidates = (
        (1,),
        (1, 4),
        (1, 4, 16),
        (1, 2, 4, 8, 16),
        (1, 2, 4, 8, 16, 32),
    )
    numjobs_candidates = (
        (1,),
        (1, 2),
        (1, 2, 4),
        (1, 2, 4, 8),
    )

    best: FioGrid | None = None
    for iods in iodepth_candidates:
        for njs in numjobs_candidates:
            cases = workloads_count * len(iods) * len(njs)
            per_case = duration_sec / max(1, cases)
            if per_case >= min_runtime_sec:
                best = FioGrid(iodepths=iods, numjobs=njs)

    return best or FioGrid(iodepths=(1,), numjobs=(1,))


def _normalize_timing(duration_sec: int, workloads_count: int, timing: FioTiming) -> FioTiming:
    cases = workloads_count * len(timing.grid.iodepths) * len(timing.grid.numjobs)
    per_case = duration_sec / max(1, cases)
    if per_case >= timing.min_runtime_sec:
        return timing

    grid = _shrink_grid(duration_sec, workloads_count, timing.min_runtime_sec)
    return FioTiming(
        grid=grid,
        min_runtime_sec=timing.min_runtime_sec,
        log_avg_msec=timing.log_avg_msec,
        ramp_time_sec=timing.ramp_time_sec,
    )


def _plan_cases(
    duration_sec: int,
    workloads: list[FioWorkload],
    timing: FioTiming,
    suite_root: Path,
) -> list[FioCase]:
    combos = list(product(workloads, timing.grid.iodepths, timing.grid.numjobs))
    if not combos:
        err_msg = "No fio cases planned"
        raise RuntimeError(err_msg)

    weights = [wl.weight for (wl, _, _) in combos]
    wsum = sum(weights)
    if wsum <= 0:
        err_msg = "Invalid fio weights sum"
        raise RuntimeError(err_msg)

    raw = [duration_sec * (w / wsum) for w in weights]
    runtimes = [max(timing.min_runtime_sec, round(x)) for x in raw]

    total = sum(runtimes)
    diff = duration_sec - total
    frac = [x - round(x) for x in raw]

    if diff > 0:
        order = sorted(range(len(runtimes)), key=lambda i: frac[i], reverse=True)
        i = 0
        while diff > 0:
            runtimes[order[i % len(order)]] += 1
            diff -= 1
            i += 1
    elif diff < 0:
        order = sorted(range(len(runtimes)), key=lambda i: frac[i])
        i = 0
        guard = 0
        while diff < 0 and guard < _DIFF_GUARD_MAX:
            idx = order[i % len(order)]
            if runtimes[idx] > timing.min_runtime_sec:
                runtimes[idx] -= 1
                diff += 1
            i += 1
            guard += 1

    cases: list[FioCase] = []
    for (wl, qd, nj), rt in zip(combos, runtimes, strict=True):
        out_dir = suite_root / wl.rw / f"bs_{wl.bs}"
        cases.append(
            FioCase(
                workload=wl,
                iodepth=qd,
                numjobs=nj,
                runtime_sec=rt,
                out_dir=out_dir,
            )
        )
    return cases


def _remote_tar(client: SSHClient, src_dir: Path, dst_tgz: Path) -> None:
    res = client(
        [
            "tar",
            "-czf",
            str(dst_tgz),
            "-C",
            str(src_dir.parent),
            str(src_dir.name),
        ]
    )
    if res.returncode:
        err_msg = res.stderr or res.stdout or "tar failed"
        raise RuntimeError(err_msg)


def _local_extract(tgz: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tgz, "r:gz") as tf:
        base = out_dir.resolve()
        for member in tf.getmembers():
            target = (out_dir / member.name).resolve()
            target_str = str(target)

            if target == base:
                continue
            if not target_str.startswith(str(base) + os.sep):
                err_msg = f"Unsafe tar member path: {member.name}"
                raise RuntimeError(err_msg)

            tf.extract(member, path=out_dir)


def _run_fio_plot(fio_plot: FioPlot, dataset_dir: Path, rw: str, title: str) -> None:
    base = ["-i", str(dataset_dir), "-r", rw, "-T", title]

    outputs = (
        (["-l"], "bar2d_qd.png"),
        (["-N"], "bar2d_nj.png"),
        (["-L", "-t", "iops"], "bar3d_iops.png"),
        (["-L", "-t", "lat"], "bar3d_lat.png"),
    )

    for extra, fname in outputs:
        out_png = dataset_dir / fname
        res = fio_plot([*base, "-o", str(out_png), *extra])
        if res.returncode:
            out = (res.stdout + "\n" + res.stderr).strip()
            logger.warning(
                "fio-plot failed: %s\n%s",
                " ".join(["fio-plot", *base, "-o", str(out_png), *extra]),
                out,
            )
