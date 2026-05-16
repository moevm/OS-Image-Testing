from __future__ import annotations

import json
import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import suppress
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from imgtests.exec.exec import common_run_command
from imgtests.exec.loaders.fio import Fio, fio_metrics_to_samples, get_available_bytes
from imgtests.exec.loaders.stress_ng import StressNg, stress_metrics_to_samples
from imgtests.exec.observers.systemd_analyze import SystemdAnalyze
from imgtests.exec.user_commands import Nproc
from imgtests.planning.profiles import CPU_SCALE_ARG_PREFIX, FIO_SIZE_RATIO_ARG_PREFIX
from imgtests.reporting.html_report import ReportGenerator
from imgtests.runner import BaseRunner
from imgtests.sizing import parse_size_to_bytes, round_bytes_to_mib_str
from imgtests.types import MetricSample, TestsCounts, TestStatus

if TYPE_CHECKING:
    from pathlib import Path

    from imgtests.database.database import ImgtestsDatabase
    from imgtests.database.models.experiment import ExperimentType
    from imgtests.exec.exec import SSHClient
    from imgtests.planning.models import LoadTask, PlanStage, TestPlan

logger = logging.getLogger(__name__)

_MIN_FIO_SIZE_BYTES = 64 * 1024**2
_MAX_FIO_SIZE_RATIO = 0.25


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
    status: TestStatus


@dataclass(frozen=True)
class StageRunResult:
    stage_name: str
    started_at: datetime
    ended_at: datetime
    tasks: tuple[TaskRunResult, ...]


@dataclass(frozen=True)
class PlanExecutionResult:
    experiment_id: int
    started_at: datetime
    ended_at: datetime
    stage_runs: tuple[StageRunResult, ...]
    metrics: tuple[MetricSample, ...]
    tests_counts: TestsCounts


class PlanExecutor(BaseRunner):
    def __init__(
        self,
        client: SSHClient | None,
        db: ImgtestsDatabase,
    ) -> None:
        super().__init__("plan_executor", client, db)
        self.client = client
        self.db = db
        self._cpu_count_cache: int | None = None

    def execute(
        self,
        plan: TestPlan,
        *,
        results_dir: Path,
        experiment_description: str,
        config_id: int | None = None,
    ) -> PlanExecutionResult:
        results_dir.mkdir(parents=True, exist_ok=True)
        started_at = datetime.now(UTC)

        experiment = self.start_experiment(
            client=self.client,
            database=self.db,
            description=experiment_description,
            experiment_type=_resolve_experiment_type(plan),
            config_id=config_id,
            started_at=started_at,
            ended_at=started_at,
        )
        experiment_id = int(experiment.experiment_id)

        stage_runs: list[StageRunResult] = []
        collected_metrics: list[MetricSample] = []
        total_count = 0
        counts = {
            TestStatus.PASSED: 0,
            TestStatus.FAILED: 0,
            TestStatus.SKIPPED: 0,
            TestStatus.BROKEN: 0,
        }
        for stage in plan.stages:
            self._wait_for_stage_offset(
                plan_started_at=started_at,
                stage_offset_sec=stage.start_offset_sec,
            )
            stage_started_at = datetime.now(UTC)

            self.db.insert_util_run_result(
                experiment_id=experiment_id,
                util_type="loader",
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
                collected_metrics.extend(task_run.metrics)

                counts[task_run.status] += 1
                total_count += 1

                self.db.insert_util_run_result(
                    experiment_id=experiment_id,
                    util_type="loader",
                    command=full_cmd,
                    result={
                        "stage_name": stage.name,
                        "subsystem": subsystem_value,
                        "tool": task_run.task.tool,
                        "utility": task_run.task.tool,
                        "command": list(task_run.command),
                        "returncode": task_run.returncode,
                        "stdout": task_run.stdout,
                        "stderr": task_run.stderr,
                        "summary": task_run.summary,
                        "metrics": [asdict(sample) for sample in task_run.metrics],
                    },
                    description=f"Task result for stage={stage.name}",
                    started_at=task_run.started_at,
                    ended_at=task_run.ended_at,
                )

            stage_runs.append(
                StageRunResult(
                    stage_name=stage.name,
                    started_at=stage_started_at,
                    ended_at=stage_ended_at,
                    tasks=tuple(task_runs),
                ),
            )

        ended_at = datetime.now(UTC)
        self.db.update_experiment_ended_at(
            experiment_id=experiment_id,
            ended_at=ended_at,
        )
        tests_counts = TestsCounts(
            total_count=total_count,
            broken_count=counts[TestStatus.BROKEN],
            passed_count=counts[TestStatus.PASSED],
            failed_count=counts[TestStatus.FAILED],
            skip_count=counts[TestStatus.SKIPPED],
        )
        self.db.update_experiment_tests_count(
            experiment.experiment_id,
            tests_counts,
        )

        result = PlanExecutionResult(
            experiment_id=experiment_id,
            started_at=started_at,
            ended_at=ended_at,
            stage_runs=tuple(stage_runs),
            metrics=tuple(collected_metrics),
            tests_counts=tests_counts,
        )
        ReportGenerator.generate_profiled_html_report(
            plan=plan,
            execution=result,
            out_dir=results_dir,
        )
        return result

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
                        status=TestStatus.FAILED,
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

        match tool:
            case "stress-ng":
                return self._run_stress_ng(stage, task, started_at)
            case "fio":
                return self._run_fio(stage, task, started_at)
            case "systemd-analyze":
                return self._run_systemd_analyze(stage, task, started_at)
            case _:
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
                    status=TestStatus.SKIPPED,
                )

    def _retry_stress_run_if_needed(
        self,
        stress: StressNg,
        stage_name: str,
        timeout_sec: int,
        args: dict[str, Any],
        exec_res: Any,
    ) -> tuple[Any, list[Any], Any] | None:
        if exec_res.returncode != stress.INITIALIZATION_FAILED_CODE:
            return None

        retry_timeout = max(5, int(timeout_sec * 0.5))

        logger.info(
            "[PLAN] stress-ng retry stage=%s rc=%s timeout=%s->%s",
            stage_name,
            exec_res.returncode,
            timeout_sec,
            retry_timeout,
        )

        exec_res2, (metrics2, summary2) = stress.run(
            timeout_sec=retry_timeout,
            **args,
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
        args = self._resolve_stress_args(args)

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
        samples = stress_metrics_to_samples(stage.name, subsystem, metrics)

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
            status=TestStatus.PASSED if exec_res.returncode == 0 else TestStatus.FAILED,
        )

    def _run_fio(
        self,
        stage: PlanStage,
        task: LoadTask,
        started_at: datetime,
    ) -> TaskRunResult:
        fio = Fio(self.client)

        args = dict(task.args or {})
        runtime_sec = int(args.pop("runtime_sec", stage.duration_sec))

        created_filename: Path | None = None
        if "filename" not in args and "directory" not in args:
            subsystem = getattr(task.subsystem, "value", str(task.subsystem))
            created_filename = fio.workdir / f"{stage.name}-{subsystem}.dat"
            args["filename"] = str(created_filename)

        if "size" in args:
            avail = (
                get_available_bytes(self.client, created_filename.parent)
                if created_filename is not None
                else None
            )
            size_value = str(args["size"])
            if size_value.startswith(FIO_SIZE_RATIO_ARG_PREFIX):
                args["size"] = self._resolve_dynamic_fio_size(size_value, avail)
            else:
                req = parse_size_to_bytes(size_value)
                if req is not None and avail is not None:
                    cap = max(_MIN_FIO_SIZE_BYTES, int(avail * _MAX_FIO_SIZE_RATIO))
                    safe = min(req, cap)
                    if safe < req:
                        args["size"] = round_bytes_to_mib_str(safe)

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
                    common_run_command(["rm", "-f", str(created_filename)], self.client)

        ended_at = datetime.now(UTC)

        payload = _try_parse_json(result.stdout)
        samples = fio_metrics_to_samples(
            payload=payload,
            stage_name=stage.name,
            subsystem=task.subsystem,
        )

        summary = None
        if payload:
            summary = {"jobs_count": len(payload.get("jobs", []))}

        logger.info("[PLAN] done stage=%s tool=fio rc=%s", stage.name, result.returncode)
        return TaskRunResult(
            task=task,
            started_at=started_at,
            ended_at=ended_at,
            command=result.cmd or ("fio",),
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            summary=summary,
            metrics=tuple(samples),
            status=TestStatus.PASSED if result.returncode == 0 else TestStatus.FAILED,
        )

    def _resolve_stress_args(self, args: dict[str, Any]) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        cpu_count: int | None = None

        for key, value in args.items():
            if isinstance(value, str) and value.startswith(CPU_SCALE_ARG_PREFIX):
                if cpu_count is None:
                    cpu_count = self._resolve_cpu_count()
                scale = _parse_dynamic_float(value, CPU_SCALE_ARG_PREFIX)
                resolved[key] = max(1, math.ceil(cpu_count * scale))
                continue

            resolved[key] = value

        return resolved

    def _resolve_dynamic_fio_size(
        self,
        raw_value: str,
        available_bytes: int | None,
    ) -> str:
        ratio = _parse_dynamic_float(raw_value, FIO_SIZE_RATIO_ARG_PREFIX)
        if available_bytes is None:
            err = (
                "Cannot resolve dynamic fio size: available bytes are unknown. "
                "Provide a concrete size or ensure free space can be detected."
            )
            raise ValueError(err)

        requested = max(_MIN_FIO_SIZE_BYTES, int(available_bytes * ratio))
        cap = max(_MIN_FIO_SIZE_BYTES, int(available_bytes * _MAX_FIO_SIZE_RATIO))
        return round_bytes_to_mib_str(min(requested, cap))

    def _resolve_cpu_count(self) -> int:
        if self._cpu_count_cache is not None:
            return self._cpu_count_cache

        result = Nproc(self.client)()
        if result.returncode != 0:
            err = "Cannot resolve CPU count for dynamic stress args: 'nproc' failed."
            raise ValueError(err)

        try:
            cpu_count = int((result.stdout or "").strip())
        except (TypeError, ValueError) as exc:
            err = "Cannot resolve CPU count for dynamic stress args: invalid 'nproc' output."
            raise ValueError(err) from exc

        if cpu_count <= 0:
            err = f"Cannot resolve CPU count for dynamic stress args: got {cpu_count}."
            raise ValueError(err)

        self._cpu_count_cache = cpu_count
        return self._cpu_count_cache

    def _run_systemd_analyze(
        self,
        stage: PlanStage,
        task: LoadTask,
        started_at: datetime,
    ) -> TaskRunResult:
        opt = task.args.get("opt", "time")
        systemd_analyze = SystemdAnalyze(self.client)
        stdout, stderr, summary, samples = "", "", None, ()
        returncode = 0
        status = TestStatus.SKIPPED

        if opt == "time":
            result = systemd_analyze.time()
            sleep_time_sec = 5
            wait_timeout_sec = stage.duration_sec

            while result.total_time < 0 and wait_timeout_sec > 0:
                self._logger.info(
                    "Waiting for system to be ready to analyze boot time, %d seconds left.",
                    wait_timeout_sec,
                )
                time.sleep(sleep_time_sec)
                wait_timeout_sec -= sleep_time_sec
                result = systemd_analyze.time()

            if result.total_time < 0:
                stderr = "Failed to get boot time, system might not be ready."
                returncode = 1
                self._logger.error(stderr)
                status = TestStatus.FAILED
            else:
                summary = result._asdict()
                samples = tuple(
                    MetricSample(
                        stage_name=stage.name,
                        subsystem=task.subsystem.value,
                        metric_name=f"systemd_time.{key}",
                        value=value,
                        label=key,
                    )
                    for key, value in result._asdict().items()
                    if value >= 0
                )
                status = TestStatus.PASSED
            stdout = str(result)

        elif opt == "critical-chain":
            services = systemd_analyze.slow_load_services()
            summary = SystemdAnalyze.metrics_to_json(services)
            stdout = str(services)
            samples = tuple(
                MetricSample(
                    stage_name=stage.name,
                    subsystem=task.subsystem.value,
                    metric_name=f"systemd_critical_chain.{service.service_name}",
                    value=service.slow_time_s,
                    label=service.service_name,
                )
                for service in services
            )
            status = TestStatus.PASSED

        else:
            returncode = 1
            stderr = f"Unknown systemd-analyze option: {opt}"
            self._logger.error(stderr)

        return TaskRunResult(
            task=task,
            started_at=started_at,
            ended_at=datetime.now(UTC),
            command=(systemd_analyze.name, opt),
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            summary=summary,
            metrics=samples,
            status=status,
        )


def _try_parse_json(text: str) -> dict[str, Any]:
    if not text:
        return {}

    raw = str(text).strip()
    if not raw:
        return {}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    return data if isinstance(data, dict) else {}


def _parse_dynamic_float(raw_value: str, prefix: str) -> float:
    try:
        value = float(raw_value.removeprefix(prefix))
    except ValueError as exc:
        err = f"Invalid dynamic value '{raw_value}'."
        raise ValueError(err) from exc

    if value <= 0:
        err = f"Dynamic value must be > 0, got '{raw_value}'."
        raise ValueError(err)

    return value


def _resolve_experiment_type(plan: TestPlan) -> ExperimentType:
    test_kind = getattr(plan.test_kind, "value", str(plan.test_kind))

    if test_kind == "stability":
        return "endurance"

    return "performance"
