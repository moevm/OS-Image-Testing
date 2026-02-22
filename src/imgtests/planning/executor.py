from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from imgtests.exec.loaders.fio import Fio
from imgtests.exec.loaders.stress_ng import StressNg
from imgtests.sysrep import get_system_info

if TYPE_CHECKING:
    from pathlib import Path

    from imgtests.database.database import ImgtestsDatabase
    from imgtests.exec.exec import SSHClient
    from imgtests.planning.models import LoadTask, PlanStage, TestPlan

logger = logging.getLogger(__name__)

_DEFAULT_FIO_WORKDIR = "/var/lib/imgtests-fio"

_DF_AVAIL_COLUMN_INDEX = 3
_DF_MIN_COLUMNS = 4
_STRESS_RETRY_RETURN_CODE = 3


@dataclass(frozen=True)
class MetricSample:
    stage_name: str
    subsystem: str
    metric_name: str
    value: float


@dataclass(frozen=True)
class TaskRunResult:
    task: LoadTask
    started_at: datetime
    ended_at: datetime
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    summary: dict[str, Any] | None
    metrics: tuple[MetricSample, ...]


@dataclass(frozen=True)
class StageRunResult:
    stage_name: str
    started_at: datetime
    ended_at: datetime
    tasks: tuple[TaskRunResult, ...]


@dataclass(frozen=True)
class PlanExecutionResult:
    experiment_id: int
    plan_path: Path
    started_at: datetime
    ended_at: datetime
    stage_runs: tuple[StageRunResult, ...]
    metrics: tuple[MetricSample, ...]


def _truncate(text: str, max_len: int = 8000) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "\n...[truncated]..."


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _try_parse_json(text: str) -> dict[str, Any]:
    if not text or not str(text).strip():
        return {}
    try:
        data = json.loads(str(text).strip())
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _parse_size_to_bytes(s: str) -> int | None:
    v = str(s).strip()
    if not v:
        return None
    if v.endswith("%"):
        return None

    mul = 1
    last = v[-1].lower()
    num = v

    if last in {"k", "m", "g", "t"}:
        num = v[:-1]
        if last == "k":
            mul = 1024
        elif last == "m":
            mul = 1024**2
        elif last == "g":
            mul = 1024**3
        elif last == "t":
            mul = 1024**4

    try:
        return int(float(num) * mul)
    except (TypeError, ValueError):
        return None


def _bytes_to_mib_str(b: int) -> str:
    mib = max(1, b // (1024**2))
    return f"{mib}M"


def _remote_df_avail_bytes(client: SSHClient, path: str) -> int | None:
    with suppress(Exception):
        res = client(("df", "-PB1", path))
        if getattr(res, "returncode", 1) != 0:
            return None

        out = (res.stdout or "").strip().splitlines()
        if not out:
            return None

        last = out[-1].split()
        if len(last) < _DF_MIN_COLUMNS:
            return None

        return int(last[_DF_AVAIL_COLUMN_INDEX])

    return None


def _halve_positive_int(value: Any, fallback: int = 1) -> int:
    try:
        return max(1, int(value) // 2)
    except (TypeError, ValueError):
        return fallback


def _build_stress_retry_args(args: dict[str, Any]) -> dict[str, Any]:
    retry_args = dict(args)

    if "vm" in retry_args:
        retry_args["vm"] = _halve_positive_int(retry_args["vm"], fallback=1)
        retry_args["vm_bytes"] = "15%"
        for key in ("vm_populate", "vm_flip", "vm_mmap", "vm_hugepage"):
            retry_args.pop(key, None)

    if "cpu" in retry_args:
        cpu_value = _safe_int(retry_args["cpu"], default=1)
        retry_args["cpu"] = 1 if cpu_value == 0 else max(1, min(cpu_value, 2))

    if "sock" in retry_args:
        retry_args["sock"] = _halve_positive_int(retry_args["sock"], fallback=1)
        if "sock_ops" in retry_args:
            try:
                retry_args["sock_ops"] = max(10_000, int(retry_args["sock_ops"]) // 3)
            except (TypeError, ValueError):
                retry_args.pop("sock_ops", None)

    if "syscall" in retry_args:
        retry_args["syscall"] = _halve_positive_int(retry_args["syscall"], fallback=1)

    return retry_args


def _stress_metric_samples(
    stage_name: str,
    subsystem: str,
    metrics: list[Any],
) -> list[MetricSample]:
    samples: list[MetricSample] = []

    for metric in metrics:
        base_metrics = (
            ("stress.bogo_ops", float(metric.bogo_ops)),
            ("stress.real_time_secs", float(metric.real_time_secs)),
            ("stress.usr_time_secs", float(metric.usr_time_secs)),
            ("stress.sys_time_secs", float(metric.sys_time_secs)),
            ("stress.bogo_ops_s_real_time", float(metric.bogo_ops_s_real_time)),
            ("stress.bogo_ops_s_usr_sys_time", float(metric.bogo_ops_s_usr_sys_time)),
            ("stress.cpu_used_per_instance", float(metric.cpu_used_per_instance)),
        )
        for metric_name, value in base_metrics:
            samples.append(MetricSample(stage_name, subsystem, metric_name, value))

        if metric.rss_max_kb is not None:
            samples.append(
                MetricSample(
                    stage_name,
                    subsystem,
                    "stress.rss_max_kb",
                    float(metric.rss_max_kb),
                )
            )

        if metric.top10_slowest:
            samples.append(
                MetricSample(
                    stage_name,
                    subsystem,
                    "stress.syscall_slowest_avg_ns",
                    float(metric.top10_slowest[0].avg_ns),
                )
            )

    return samples


def _fio_op_samples(
    stage_name: str,
    subsystem: str,
    op: str,
    op_data: dict[str, Any],
    wanted_p: dict[str, int],
) -> list[MetricSample]:
    out: list[MetricSample] = []

    iops = _safe_float(op_data.get("iops"))
    bw = _safe_float(op_data.get("bw"))
    runtime_ms = _safe_float(op_data.get("runtime"))

    clat = op_data.get("clat_ns") or {}
    clat_mean = _safe_float(clat.get("mean")) if isinstance(clat, dict) else None

    if iops is not None:
        out.append(MetricSample(stage_name, subsystem, f"fio.{op}.iops", iops))
    if bw is not None:
        out.append(MetricSample(stage_name, subsystem, f"fio.{op}.bw_kib_s", bw))
    if runtime_ms is not None:
        out.append(MetricSample(stage_name, subsystem, f"fio.{op}.runtime_ms", runtime_ms))
    if clat_mean is not None:
        out.append(MetricSample(stage_name, subsystem, f"fio.{op}.clat_mean_ns", clat_mean))

    pct = clat.get("percentile") if isinstance(clat, dict) else None
    if isinstance(pct, dict):
        for key, p_int in wanted_p.items():
            fv = _safe_float(pct.get(key))
            if fv is not None:
                out.append(MetricSample(stage_name, subsystem, f"fio.{op}.clat_p{p_int}_ns", fv))

    return out


class PlanExecutor:
    def __init__(
        self,
        client: SSHClient,
        db: ImgtestsDatabase,
        results_dir: Path,
        config_id: int | None = None,
        experiment_description: str | None = None,
    ) -> None:
        self.client = client
        self.db = db
        self.results_dir = results_dir
        self.config_id = config_id
        self.experiment_description = experiment_description or "Auto-generated load test plan"
        self.fio_workdir = _DEFAULT_FIO_WORKDIR

    def execute(self, plan: TestPlan) -> PlanExecutionResult:
        self.results_dir.mkdir(parents=True, exist_ok=True)
        started_at = datetime.now(UTC)

        plan_path = self.results_dir / f"plan_{plan.plan_id}.json"
        plan_path.write_text(
            json.dumps(plan.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        cfg_id = self._ensure_config_id()

        experiment = self.db.insert_experiment(
            config_id=cfg_id,
            description=self.experiment_description,
            experiment_type=getattr(plan.test_kind, "value", str(plan.test_kind)),
            started_at=started_at,
            ended_at=started_at,
        )
        experiment_id = int(experiment.experiment_id)

        self.db.insert_loader(
            experiment_id=experiment_id,
            command="plan.json",
            result=plan.to_dict(),
            description="Generated execution plan",
            started_at=started_at,
            ended_at=started_at,
        )

        stage_runs: list[StageRunResult] = []
        collected_metrics: list[MetricSample] = []

        for stage in plan.stages:
            self._wait_for_stage_offset(
                plan_started_at=started_at,
                stage_offset_sec=stage.start_offset_sec,
            )
            stage_started_at = datetime.now(UTC)

            self.db.insert_loader(
                experiment_id=experiment_id,
                command="plan-stage",
                result={
                    "stage_name": stage.name,
                    "start_offset_sec": stage.start_offset_sec,
                    "duration_sec": stage.duration_sec,
                    "pattern": getattr(stage.pattern, "value", str(stage.pattern)),
                    "tasks": [t.to_dict() for t in stage.tasks],
                },
                description="Planned stage",
                started_at=stage_started_at,
                ended_at=stage_started_at,
            )

            task_runs = self._run_stage(stage)
            stage_ended_at = datetime.now(UTC)

            for task_run in task_runs:
                full_cmd = " ".join(task_run.command) if task_run.command else ""
                subsystem_value = getattr(
                    task_run.task.subsystem,
                    "value",
                    str(task_run.task.subsystem),
                )

                self.db.insert_loader(
                    experiment_id=experiment_id,
                    command=full_cmd,
                    result={
                        "stage_name": stage.name,
                        "subsystem": subsystem_value,
                        "tool": task_run.task.tool,
                        "returncode": task_run.returncode,
                        "command_full": full_cmd,
                        "stdout": _truncate(task_run.stdout),
                        "stderr": _truncate(task_run.stderr),
                        "summary": task_run.summary,
                    },
                    description=f"Task result for stage={stage.name}",
                    started_at=task_run.started_at,
                    ended_at=task_run.ended_at,
                )

                for sample in task_run.metrics:
                    collected_metrics.append(sample)
                    self.db.insert_observer(
                        experiment_id=experiment_id,
                        command=f"{task_run.task.tool}:{sample.metric_name}",
                        result={
                            "stage_name": sample.stage_name,
                            "subsystem": sample.subsystem,
                            "metric_name": sample.metric_name,
                            "value": sample.value,
                        },
                        description="Observed numeric metric",
                        started_at=task_run.started_at,
                        ended_at=task_run.ended_at,
                    )

            stage_runs.append(
                StageRunResult(
                    stage_name=stage.name,
                    started_at=stage_started_at,
                    ended_at=stage_ended_at,
                    tasks=tuple(task_runs),
                )
            )

        ended_at = datetime.now(UTC)
        self.db.update_experiment_ended_at(
            experiment_id=experiment_id,
            ended_at=ended_at,
        )

        return PlanExecutionResult(
            experiment_id=experiment_id,
            plan_path=plan_path,
            started_at=started_at,
            ended_at=ended_at,
            stage_runs=tuple(stage_runs),
            metrics=tuple(collected_metrics),
        )

    def _ensure_config_id(self) -> int:
        if self.config_id is not None:
            return int(self.config_id)
        sys_info = get_system_info(self.client)
        cfg = self.db.insert_from_system_info(sys_info)
        return int(cfg.config_id)

    def _wait_for_stage_offset(
        self,
        plan_started_at: datetime,
        stage_offset_sec: int,
    ) -> None:
        target_ts = plan_started_at.timestamp() + max(0, int(stage_offset_sec))
        now_ts = datetime.now(UTC).timestamp()
        wait_sec = target_ts - now_ts
        if wait_sec > 0:
            time.sleep(wait_sec)

    def _run_stage(self, stage: PlanStage) -> list[TaskRunResult]:
        if not stage.tasks:
            return []

        results_by_idx: dict[int, TaskRunResult] = {}
        max_workers = max(1, len(stage.tasks))

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_map = {
                pool.submit(self._run_task, stage, task): (idx, task)
                for idx, task in enumerate(stage.tasks)
            }

            for future in as_completed(future_map):
                idx, task = future_map[future]
                try:
                    results_by_idx[idx] = future.result()
                except Exception as exc:
                    now = datetime.now(UTC)
                    logger.exception("Task failed with exception.")
                    results_by_idx[idx] = TaskRunResult(
                        task=task,
                        started_at=now,
                        ended_at=now,
                        command=("internal-error",),
                        returncode=1,
                        stdout="",
                        stderr=str(exc),
                        summary={"error": str(exc)},
                        metrics=(),
                    )

        return [results_by_idx[i] for i in range(len(stage.tasks))]

    def _run_task(self, stage: PlanStage, task: LoadTask) -> TaskRunResult:
        tool = (task.tool or "").strip().lower().replace("_", "-")
        started_at = datetime.now(UTC)
        subsystem_value = getattr(task.subsystem, "value", str(task.subsystem))

        logger.info(
            "[PLAN] run stage=%s tool=%s subsystem=%s dur=%ss",
            stage.name,
            tool,
            subsystem_value,
            stage.duration_sec,
        )

        if tool in {"stress-ng", "stressng"}:
            return self._run_stress_ng(stage, task, started_at)

        if tool == "fio":
            return self._run_fio(stage, task, started_at)

        now = datetime.now(UTC)
        return TaskRunResult(
            task=task,
            started_at=started_at,
            ended_at=now,
            command=("unknown-tool", tool),
            returncode=1,
            stdout="",
            stderr=f"Unknown tool: {tool}",
            summary={"error": f"Unknown tool: {tool}"},
            metrics=(),
        )

    def _retry_stress_run_if_needed(
        self,
        stress: StressNg,
        stage_name: str,
        timeout_sec: int,
        args: dict[str, Any],
        exec_res: Any,
    ) -> tuple[Any, list[Any], Any] | None:
        if exec_res.returncode != _STRESS_RETRY_RETURN_CODE:
            return None

        retry_args = _build_stress_retry_args(args)
        retry_timeout = max(5, int(timeout_sec * 0.5))

        logger.info(
            "[PLAN] stress-ng retry stage=%s rc=%s timeout=%s->%s",
            stage_name,
            _STRESS_RETRY_RETURN_CODE,
            timeout_sec,
            retry_timeout,
        )

        exec_res2, (metrics2, summary2) = stress.run(
            timeout_sec=retry_timeout,
            **retry_args,
        )
        if exec_res2.returncode == 0:
            return exec_res2, metrics2, summary2
        return None

    def _run_stress_ng(
        self,
        stage: PlanStage,
        task: LoadTask,
        started_at: datetime,
    ) -> TaskRunResult:
        stress = StressNg(self.client)

        args = dict(task.args or {})
        timeout_sec = int(args.pop("timeout_sec", stage.duration_sec))
        args.pop("verify", None)

        exec_res, (metrics, summary) = stress.run(timeout_sec=timeout_sec, **args)

        retry_result = self._retry_stress_run_if_needed(
            stress=stress,
            stage_name=stage.name,
            timeout_sec=timeout_sec,
            args=args,
            exec_res=exec_res,
        )
        if retry_result is not None:
            exec_res, metrics, summary = retry_result

        ended_at = datetime.now(UTC)
        subsystem = getattr(task.subsystem, "value", str(task.subsystem))
        samples = _stress_metric_samples(stage.name, subsystem, metrics)

        summary_dict = summary._asdict() if summary else None
        logger.info(
            "[PLAN] done stage=%s tool=stress-ng rc=%s",
            stage.name,
            exec_res.returncode,
        )
        return TaskRunResult(
            task=task,
            started_at=started_at,
            ended_at=ended_at,
            command=exec_res.cmd,
            returncode=exec_res.returncode,
            stdout=exec_res.stdout,
            stderr=exec_res.stderr,
            summary=summary_dict,
            metrics=tuple(samples),
        )

    def _run_fio(
        self,
        stage: PlanStage,
        task: LoadTask,
        started_at: datetime,
    ) -> TaskRunResult:
        fio = Fio(self.client)
        self.client(("mkdir", "-p", self.fio_workdir))

        args = dict(task.args or {})
        runtime_sec = int(args.pop("runtime_sec", stage.duration_sec))

        created_filename: str | None = None
        if "filename" not in args and "directory" not in args:
            subsystem = getattr(task.subsystem, "value", str(task.subsystem))
            created_filename = f"{self.fio_workdir}/{stage.name}-{subsystem}.dat"
            args["filename"] = created_filename

        if "size" in args:
            req = _parse_size_to_bytes(str(args["size"]))
            avail = _remote_df_avail_bytes(self.client, self.fio_workdir)
            if req is not None and avail is not None:
                cap = max(64 * 1024**2, int(avail * 0.25))
                safe = min(req, cap)
                if safe < req:
                    args["size"] = _bytes_to_mib_str(safe)

        fio_name = args.pop(
            "name",
            f"{stage.name}-{getattr(task.subsystem, 'value', str(task.subsystem))}",
        )

        try:
            result = fio.run(
                name=fio_name,
                runtime=runtime_sec,
                time_based=True,
                group_reporting=True,
                direct=1,
                ioengine=args.pop("ioengine", "libaio"),
                **args,
            )
        finally:
            if created_filename:
                with suppress(Exception):
                    self.client(("rm", "-f", created_filename))

        ended_at = datetime.now(UTC)

        payload = _try_parse_json(result.stdout)
        samples = self._fio_samples(
            payload=payload,
            stage_name=stage.name,
            subsystem=getattr(task.subsystem, "value", str(task.subsystem)),
        )

        summary = None
        if payload:
            summary = {"jobs_count": len(payload.get("jobs", []))}

        logger.info("[PLAN] done stage=%s tool=fio rc=%s", stage.name, result.returncode)
        return TaskRunResult(
            task=task,
            started_at=started_at,
            ended_at=ended_at,
            command=result.cmd if result.cmd else ("fio",),
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            summary=summary,
            metrics=tuple(samples),
        )

    def _fio_samples(
        self,
        payload: dict[str, Any],
        stage_name: str,
        subsystem: str,
    ) -> list[MetricSample]:
        jobs = payload.get("jobs", [])
        if not isinstance(jobs, list):
            return []

        wanted_p = {
            "50.000000": 50,
            "90.000000": 90,
            "95.000000": 95,
            "99.000000": 99,
            "99.900000": 999,
        }

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
                        subsystem=subsystem,
                        op=op,
                        op_data=op_data,
                        wanted_p=wanted_p,
                    )
                )

        return out
