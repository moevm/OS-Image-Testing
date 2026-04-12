from __future__ import annotations

from typing import TYPE_CHECKING

from imgtests.planning.models import (
    LoadPattern,
    PlanRequest,
    PlanStage,
    TestKind,
    TestPlan,
)
from imgtests.planning.profiles import PROFILE_LAYOUTS, build_stage_tasks, build_task

if TYPE_CHECKING:
    from collections.abc import Iterable

    from imgtests.types import Subsystem

_ALLOC_GUARD_LIMIT = 100_000


def build_plan(request: PlanRequest) -> TestPlan:
    if request.duration_sec <= 0:
        err = f"duration_sec must be > 0, got {request.duration_sec}"
        raise ValueError(err)

    if not request.subsystems:
        msg = "At least one subsystem must be provided."
        raise ValueError(msg)

    ordered_subsystems = tuple(sorted(request.subsystems, key=lambda item: item.value))
    stages: list[PlanStage] = []

    if request.pattern is not None:
        if request.test_kind == TestKind.ISOLATED:
            stages = _build_isolated_stages(
                request.duration_sec,
                ordered_subsystems,
                pattern=request.pattern,
            )
        else:
            tasks = build_stage_tasks(
                request.test_kind,
                request.subsystems,
                request.pattern,
                request.duration_sec,
            )
            stages = [
                PlanStage(
                    name=f"{request.test_kind.value}_{request.pattern.value}",
                    start_offset_sec=0,
                    duration_sec=request.duration_sec,
                    pattern=request.pattern,
                    tasks=tasks,
                )
            ]
    elif request.test_kind == TestKind.ISOLATED:
        stages = _build_isolated_stages(request.duration_sec, ordered_subsystems)
    else:
        templates = PROFILE_LAYOUTS[request.test_kind]
        durations = _allocate_durations(
            request.duration_sec,
            [tpl.weight for tpl in templates],
        )

        offset = 0
        for tpl, dur in zip(templates, durations, strict=True):
            tasks = build_stage_tasks(
                request.test_kind,
                request.subsystems,
                tpl.pattern,
                dur,
            )
            stages.append(
                PlanStage(
                    name=tpl.name,
                    start_offset_sec=offset,
                    duration_sec=dur,
                    pattern=tpl.pattern,
                    tasks=tasks,
                )
            )
            offset += dur

    return TestPlan.new(
        duration_sec=request.duration_sec,
        subsystems=request.subsystems,
        test_kind=request.test_kind,
        stages=tuple(stages),
    )


def _build_isolated_stages(
    duration_sec: int,
    subsystems: Iterable[Subsystem],
    pattern: LoadPattern = LoadPattern.BALANCED,
) -> list[PlanStage]:
    subsystems_list = list(subsystems)
    durations = _allocate_durations(duration_sec, [1.0] * len(subsystems_list))
    stages: list[PlanStage] = []
    offset = 0

    for subsystem, stage_duration in zip(subsystems_list, durations, strict=True):
        task = build_task(subsystem, pattern, stage_duration)
        stages.append(
            PlanStage(
                name=f"isolated_{subsystem.value}",
                start_offset_sec=offset,
                duration_sec=stage_duration,
                pattern=pattern,
                tasks=(task,),
            )
        )
        offset += stage_duration

    return stages


def _allocate_durations(total_sec: int, weights: list[float]) -> list[int]:
    _validate_allocation_inputs(total_sec, weights)

    weight_sum = sum(weights)
    raw = [total_sec * (w / weight_sum) for w in weights]
    base = [int(x) for x in raw]
    base = [max(1, value) for value in base]

    diff = total_sec - sum(base)
    if diff > 0:
        _distribute_positive_diff(raw, base, diff)
    elif diff < 0:
        _distribute_negative_diff(raw, base, diff)

    if sum(base) != total_sec:
        base[-1] += total_sec - sum(base)

    return base


def _validate_allocation_inputs(total_sec: int, weights: list[float]) -> None:
    if total_sec <= 0:
        msg = "total_sec must be > 0."
        raise ValueError(msg)

    if not weights:
        msg = "weights must not be empty."
        raise ValueError(msg)

    if sum(weights) <= 0:
        msg = "weights sum must be > 0."
        raise ValueError(msg)


def _distribute_positive_diff(raw: list[float], base: list[int], diff: int) -> None:
    frac_idx = sorted(range(len(raw)), key=lambda i: raw[i] - int(raw[i]), reverse=True)
    idx = 0
    remaining = diff

    while remaining > 0:
        base[frac_idx[idx % len(frac_idx)]] += 1
        remaining -= 1
        idx += 1


def _distribute_negative_diff(raw: list[float], base: list[int], diff: int) -> None:
    frac_idx = sorted(range(len(raw)), key=lambda i: raw[i] - int(raw[i]))
    idx = 0
    guard = 0
    remaining = diff

    while remaining < 0 and guard < _ALLOC_GUARD_LIMIT:
        target_idx = frac_idx[idx % len(frac_idx)]
        if base[target_idx] > 1:
            base[target_idx] -= 1
            remaining += 1
        idx += 1
        guard += 1

    if remaining < 0:
        base[-1] = max(1, base[-1] + remaining)
