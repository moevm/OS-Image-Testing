from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import suppress
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from imgtests.exec.exec import common_run_command
from imgtests.exec.loaders.fio import Fio, fio_metrics_to_samples, get_available_bytes
from imgtests.exec.loaders.stress_ng import StressNg, stress_metrics_to_samples
from imgtests.runner import BaseRunner
from imgtests.sizing import parse_size_to_bytes, round_bytes_to_mib_str
from imgtests.types import MetricSample, Subsystem

if TYPE_CHECKING:
    from pathlib import Path

    from imgtests.database.database import ExperimentType, ImgtestsDatabase
    from imgtests.exec.exec import SSHClient
    from imgtests.planning.models import LoadTask, PlanStage, TestPlan

logger = logging.getLogger(__name__)


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
    started_at: datetime
    ended_at: datetime
    stage_runs: tuple[StageRunResult, ...]
    metrics: tuple[MetricSample, ...]


class PlanExecutor(BaseRunner):
    def __init__(
        self,
        client: SSHClient,
        db: ImgtestsDatabase,
    ) -> None:
        self.client = client
        self.db = db

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
                collected_metrics.extend(task_run.metrics)

                self.db.insert_loader(
                    experiment_id=experiment_id,
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
                )
            )

        ended_at = datetime.now(UTC)
        self.db.update_experiment_ended_at(
            experiment_id=experiment_id,
            ended_at=ended_at,
        )

        return PlanExecutionResult(
            experiment_id=experiment_id,
            started_at=started_at,
            ended_at=ended_at,
            stage_runs=tuple(stage_runs),
            metrics=tuple(collected_metrics),
        )

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
            req = parse_size_to_bytes(str(args["size"]))
            avail = (
                get_available_bytes(self.client, created_filename.parent)
                if created_filename is not None
                else None
            )
            if req is not None and avail is not None:
                cap = max(64 * 1024**2, int(avail * 0.25))
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
            command=result.cmd if result.cmd else ("fio",),
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            summary=summary,
            metrics=tuple(samples),
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


def _resolve_experiment_type(plan: TestPlan) -> ExperimentType:
    test_kind = getattr(plan.test_kind, "value", str(plan.test_kind))

    if set(plan.subsystems) == set(Subsystem):
        return "all"

    if test_kind == "stability":
        return "endurance"

    return "performance"
