"""Plan builder module for image testing.

This module provides functionality for building test plans based on various
parameters such as test kind, load pattern, subsystems, and duration. It handles
the allocation of time across different stages and subsystems according to
specified profiles and patterns.

Public functions:
    - build_plan: Build a complete TestPlan from a PlanRequest.

Example:
    To build a test plan for a load test:

    >>> from imgtests.planning.plan_builder import build_plan
    >>> from imgtests.planning.models import PlanRequest, TestKind, LoadPattern
    >>> from imgtests.types import Subsystem
    >>> request = PlanRequest(
    ...     duration_sec=300,
    ...     subsystems=frozenset({Subsystem.MEMORY, Subsystem.NETWORK}),
    ...     test_kind=TestKind.LOAD,
    ...     pattern=LoadPattern.BALANCED,
    ... )
    >>> plan = build_plan(request)
    >>> len(plan.stages)
    3
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

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

_ALLOC_GUARD_LIMIT: Final = 10_000


def build_plan(request: PlanRequest) -> TestPlan:
    """Build a TestPlan from a PlanRequest.

    Args:
        request: The plan request containing duration, subsystems, test kind,
            and optional load pattern.

    Returns:
        A complete TestPlan with stages and tasks.

    Raises:
        ValueError: If duration_sec is <= 0 or if no subsystems are provided.
    """
    if request.duration_sec <= 0:
        err = f"duration_sec must be > 0, got {request.duration_sec}"
        raise ValueError(err)

    if not request.subsystems:
        msg = "At least one subsystem must be provided."
        raise ValueError(msg)

    ordered_subsystems = tuple(sorted(request.subsystems, key=lambda item: item.value))
    stages: list[PlanStage] = []

    if request.pattern is not None:
        if request.test_kind is TestKind.ISOLATED:
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
                ),
            ]
    elif request.test_kind is TestKind.ISOLATED:
        stages = _build_isolated_stages(request.duration_sec, ordered_subsystems)
    else:
        templates = PROFILE_LAYOUTS[request.test_kind]
        durations = _allocate_durations(
            request.duration_sec,
            [template.weight for template in templates],
        )

        offset = 0
        for template, duration in zip(templates, durations, strict=True):
            tasks = build_stage_tasks(
                request.test_kind,
                request.subsystems,
                template.pattern,
                duration,
            )
            stages.append(
                PlanStage(
                    name=template.name,
                    start_offset_sec=offset,
                    duration_sec=duration,
                    pattern=template.pattern,
                    tasks=tasks,
                ),
            )
            offset += duration

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
    """Build isolated stages for each subsystem.

    Args:
        duration_sec: Total duration for all stages in seconds.
        subsystems: Iterable of subsystems to create stages for.
        pattern: Load pattern to use for all stages.

    Returns:
        A list of PlanStage objects, one for each subsystem.
    """
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
            ),
        )
        offset += stage_duration

    return stages


def _allocate_durations(total_sec: int, weights: list[float]) -> list[int]:
    """Allocate total duration across multiple stages based on weights.

    Args:
        total_sec: Total duration in seconds to allocate.
        weights: List of weights for each stage.

    Returns:
        A list of integers representing allocated durations for each stage,
        such that the sum equals total_sec.

    Raises:
        ValueError: If total_sec <= 0, weights is empty, or any element in weights <= 0.0.
    """
    _validate_allocation_inputs(total_sec, weights)

    weight_sum = sum(weights)
    raw = [total_sec * (weight / weight_sum) for weight in weights]
    base = [max(1, int(seconds)) for seconds in raw]

    diff = total_sec - sum(base)
    if diff > 0:
        _distribute_positive_diff(raw, base, diff)
    elif diff < 0:
        _distribute_negative_diff(raw, base, diff)

    if sum(base) != total_sec:
        base[-1] += total_sec - sum(base)
        base[-1] = max(1, base[-1])

    return base


def _validate_allocation_inputs(total_sec: int, weights: list[float]) -> None:
    """Validate inputs for duration allocation.

    Args:
        total_sec: Total duration in seconds.
        weights: List of weights for allocation.

    Raises:
        ValueError: If total_sec <= 0, weights is empty, or any element in weights <= 0.0.
    """
    if total_sec <= 0:
        msg = "total_sec must be > 0."
        raise ValueError(msg)

    if not weights:
        msg = "weights must not be empty."
        raise ValueError(msg)

    for weight in weights:
        if weight <= 0.0:
            msg = "all weights must be > 0."
            raise ValueError(msg)


def _distribute_positive_diff(raw: list[float], base: list[int], diff: int) -> None:
    """Distribute positive difference by incrementing stages with highest fractions.

    Args:
        raw: List of raw float values before rounding.
        base: List of base integer values after truncation.
        diff: Positive difference to distribute.
    """
    frac_idx = sorted(range(len(raw)), key=lambda i: raw[i] - int(raw[i]), reverse=True)
    idx = 0
    remaining = diff

    while remaining > 0:
        base[frac_idx[idx % len(frac_idx)]] += 1
        remaining -= 1
        idx += 1


def _distribute_negative_diff(raw: list[float], base: list[int], diff: int) -> None:
    """Distribute negative difference by decrementing stages with lowest fractions.

    Args:
        raw: List of raw float values before rounding.
        base: List of base integer values after truncation.
        diff: Negative difference to distribute.
    """
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
