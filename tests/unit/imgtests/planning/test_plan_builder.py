"""Unit tests for the plan_builder module."""

import pytest

from imgtests.planning.models import LoadPattern, PlanRequest
from imgtests.planning.models import TestKind as ProfilesTestKind
from imgtests.planning.plan_builder import (
    _allocate_durations,
    _build_isolated_stages,
    _distribute_negative_diff,
    _distribute_positive_diff,
    _validate_allocation_inputs,
    build_plan,
)
from imgtests.types import Subsystem


class TestBuildPlan:
    """Tests for the build_plan function."""

    def test_build_plan_single_subsystem_isolated(self) -> None:
        """Test building a plan for a single subsystem with isolated test kind."""
        duration_sec = 60
        request = PlanRequest(
            duration_sec=duration_sec,
            subsystems=frozenset({Subsystem.MEMORY}),
            test_kind=ProfilesTestKind.ISOLATED,
        )
        plan = build_plan(request)

        assert plan.duration_sec == duration_sec
        assert len(plan.stages) == 1
        assert plan.stages[0].name == "isolated_memory"
        assert plan.stages[0].duration_sec == duration_sec
        assert plan.stages[0].pattern == LoadPattern.BALANCED
        assert len(plan.stages[0].tasks) == 1
        assert plan.stages[0].tasks[0].subsystem == Subsystem.MEMORY

    def test_build_plan_multiple_subsystems_isolated(self) -> None:
        """Test building a plan for multiple subsystems with isolated test kind."""
        duration_sec = 120
        request = PlanRequest(
            duration_sec=duration_sec,
            subsystems=frozenset({Subsystem.MEMORY, Subsystem.NETWORK}),
            test_kind=ProfilesTestKind.ISOLATED,
        )
        plan = build_plan(request)

        assert plan.duration_sec == duration_sec
        assert len(plan.stages) == 2  # noqa: PLR2004
        # Subsystems should be sorted by name
        assert plan.stages[0].name == "isolated_memory"
        assert plan.stages[1].name == "isolated_network"

    def test_build_plan_with_pattern(self) -> None:
        duration_sec = 180
        request = PlanRequest(
            duration_sec=duration_sec,
            subsystems=frozenset({Subsystem.MEMORY, Subsystem.NETWORK}),
            test_kind=ProfilesTestKind.LOAD,
            pattern=LoadPattern.BALANCED,
        )
        plan = build_plan(request)

        assert plan.duration_sec == duration_sec
        assert len(plan.stages) == 1
        assert plan.stages[0].name == "load_balanced"
        assert plan.stages[0].duration_sec == duration_sec
        assert plan.stages[0].pattern == LoadPattern.BALANCED

    def test_build_plan_with_pattern_isolated(self) -> None:
        duration_sec = 180
        request = PlanRequest(
            duration_sec=duration_sec,
            subsystems=frozenset({Subsystem.MEMORY, Subsystem.NETWORK}),
            test_kind=ProfilesTestKind.ISOLATED,
            pattern=LoadPattern.BALANCED,
        )
        plan = build_plan(request)

        assert plan.duration_sec == duration_sec
        assert len(plan.stages) == 2  # noqa: PLR2004
        assert plan.stages[0].name == "isolated_memory"
        assert plan.stages[0].duration_sec == duration_sec / 2
        assert plan.stages[0].pattern == LoadPattern.BALANCED
        assert plan.stages[1].name == "isolated_network"
        assert plan.stages[1].duration_sec == duration_sec / 2
        assert plan.stages[1].pattern == LoadPattern.BALANCED

    def test_build_plan_load_kind(self) -> None:
        duration_sec = 300
        request = PlanRequest(
            duration_sec=duration_sec,
            subsystems=frozenset({Subsystem.MEMORY, Subsystem.NETWORK}),
            test_kind=ProfilesTestKind.LOAD,
        )
        plan = build_plan(request)

        assert plan.duration_sec == duration_sec
        assert len(plan.stages) == 3  # noqa: PLR2004
        assert plan.stages[0].name == "warmup"
        assert plan.stages[1].name == "main"
        assert plan.stages[2].name == "cooldown"

    def test_build_plan_stress_kind(self) -> None:
        duration_sec = 240
        request = PlanRequest(
            duration_sec=duration_sec,
            subsystems=frozenset({Subsystem.MEMORY}),
            test_kind=ProfilesTestKind.STRESS,
        )
        plan = build_plan(request)

        assert plan.duration_sec == duration_sec
        assert len(plan.stages) == 3  # noqa: PLR2004
        assert plan.stages[0].name == "ramp"
        assert plan.stages[1].name == "peak"
        assert plan.stages[2].name == "cooldown"

    def test_build_plan_stability_kind(self) -> None:
        duration_sec = 600
        request = PlanRequest(
            duration_sec=duration_sec,
            subsystems=frozenset({Subsystem.MEMORY}),
            test_kind=ProfilesTestKind.STABILITY,
        )
        plan = build_plan(request)

        assert plan.duration_sec == duration_sec
        assert len(plan.stages) == 1
        assert plan.stages[0].name == "soak"
        assert plan.stages[0].pattern == LoadPattern.BALANCED

    def test_build_plan_scalability_kind(self) -> None:
        duration_sec = 400
        request = PlanRequest(
            duration_sec=duration_sec,
            subsystems=frozenset({Subsystem.MEMORY}),
            test_kind=ProfilesTestKind.SCALABILITY,
        )
        plan = build_plan(request)

        assert plan.duration_sec == duration_sec
        assert len(plan.stages) == 4  # noqa: PLR2004
        assert plan.stages[0].name == "step_soft"
        assert plan.stages[1].name == "step_balanced"
        assert plan.stages[2].name == "step_intense"
        assert plan.stages[3].name == "step_extreme"

    def test_build_plan_volume_kind(self) -> None:
        duration_sec = 360
        request = PlanRequest(
            duration_sec=duration_sec,
            subsystems=frozenset({Subsystem.FILE}),
            test_kind=ProfilesTestKind.VOLUME,
        )
        plan = build_plan(request)

        assert plan.duration_sec == duration_sec
        assert len(plan.stages) == 2  # noqa: PLR2004
        assert plan.stages[0].name == "prefill"
        assert plan.stages[1].name == "bulk"

    def test_build_plan_spike_kind(self) -> None:
        duration_sec = 300
        request = PlanRequest(
            duration_sec=duration_sec,
            subsystems=frozenset({Subsystem.MEMORY}),
            test_kind=ProfilesTestKind.SPIKE,
        )
        plan = build_plan(request)

        assert plan.duration_sec == duration_sec
        assert len(plan.stages) == 3  # noqa: PLR2004
        assert plan.stages[0].name == "baseline_1"
        assert plan.stages[1].name == "spike"
        assert plan.stages[2].name == "baseline_2"

    def test_build_plan_diagnostic_kind(self) -> None:
        """Test building a plan for diagnostic test kind."""
        duration_sec = 60
        request = PlanRequest(
            duration_sec=duration_sec,
            subsystems=frozenset({Subsystem.MEMORY}),
            test_kind=ProfilesTestKind.DIAGNOSTIC,
        )
        plan = build_plan(request)

        assert plan.duration_sec == duration_sec
        assert len(plan.stages) == 1
        assert plan.stages[0].name == "systemd_boot"
        assert plan.stages[0].pattern == LoadPattern.SOFT

    def test_build_plan_invalid_duration(self) -> None:
        """Test that invalid duration raises ValueError."""
        request = PlanRequest(
            duration_sec=-10,
            subsystems=frozenset({Subsystem.MEMORY}),
            test_kind=ProfilesTestKind.LOAD,
        )

        with pytest.raises(ValueError, match="duration_sec must be > 0"):
            build_plan(request)

    def test_build_plan_empty_subsystems(self) -> None:
        """Test that empty subsystems raises ValueError."""
        request = PlanRequest(
            duration_sec=60,
            subsystems=frozenset(),
            test_kind=ProfilesTestKind.LOAD,
        )

        with pytest.raises(ValueError, match="At least one subsystem must be provided"):
            build_plan(request)

    def test_build_plan_durations_allocation(self) -> None:
        """Test that durations are correctly allocated across stages."""
        # Use load kind with weights 0.20, 0.60, 0.20 = 1.0 total
        request = PlanRequest(
            duration_sec=100,
            subsystems=frozenset({Subsystem.MEMORY}),
            test_kind=ProfilesTestKind.LOAD,
        )
        plan = build_plan(request)

        assert plan.stages[0].duration_sec == 20  # noqa: PLR2004
        assert plan.stages[1].duration_sec == 60  # noqa: PLR2004
        assert plan.stages[2].duration_sec == 20  # noqa: PLR2004

    def test_build_plan_durations_allocation_with_remainder(self) -> None:
        """Test duration allocation with remainder distribution."""
        # Use load kind with weights 0.20, 0.60, 0.20 = 1.0 total
        duration_sec = 101
        request = PlanRequest(
            duration_sec=duration_sec,
            subsystems=frozenset({Subsystem.MEMORY}),
            test_kind=ProfilesTestKind.LOAD,
        )
        plan = build_plan(request)

        # Expected: 20, 61, 20 (remainder goes to middle stage with highest weight)
        assert sum(stage.duration_sec for stage in plan.stages) == duration_sec

    def test_build_plan_isolated_durations_equal(self) -> None:
        """Test that isolated stages get equal duration allocation."""
        request = PlanRequest(
            duration_sec=90,
            subsystems=frozenset({Subsystem.MEMORY, Subsystem.NETWORK, Subsystem.FILE}),
            test_kind=ProfilesTestKind.ISOLATED,
        )
        plan = build_plan(request)

        # 3 subsystems, 90 seconds total -> 30 each
        assert len(plan.stages) == 3  # noqa: PLR2004
        assert plan.stages[0].duration_sec == 30  # noqa: PLR2004
        assert plan.stages[1].duration_sec == 30  # noqa: PLR2004
        assert plan.stages[2].duration_sec == 30  # noqa: PLR2004


class TestBuildIsolatedStages:
    """Tests for the _build_isolated_stages function."""

    def test_build_isolated_stages_single_subsystem(self) -> None:
        """Test building isolated stages for a single subsystem."""
        duration_sec = 60
        stages = _build_isolated_stages(duration_sec, [Subsystem.MEMORY])

        assert len(stages) == 1
        assert stages[0].name == "isolated_memory"
        assert stages[0].duration_sec == duration_sec
        assert stages[0].pattern == LoadPattern.BALANCED

    def test_build_isolated_stages_multiple_subsystems(self) -> None:
        """Test building isolated stages for multiple subsystems."""
        duration_sec = 90
        stages = _build_isolated_stages(duration_sec, [Subsystem.MEMORY, Subsystem.NETWORK])

        assert len(stages) == 2  # noqa: PLR2004
        assert stages[0].name == "isolated_memory"
        assert stages[1].name == "isolated_network"
        assert stages[0].duration_sec == duration_sec / 2
        assert stages[1].duration_sec == duration_sec / 2

    def test_build_isolated_stages_custom_pattern(self) -> None:
        """Test building isolated stages with a custom load pattern."""
        stages = _build_isolated_stages(60, [Subsystem.MEMORY], pattern=LoadPattern.INTENSE)

        assert len(stages) == 1
        assert stages[0].name == "isolated_memory"
        assert stages[0].pattern == LoadPattern.INTENSE


class TestAllocateDurations:
    def test_allocate_durations_equal_weights_positive_diff(self) -> None:
        assert _allocate_durations(100, [1.0, 1.0, 1.0]) == [34, 33, 33]

    def test_allocate_durations_equal_weights_negative_diff(self) -> None:
        assert _allocate_durations(3, [1.0, 1.0, 1.0, 1.0]) == [1, 1, 1, 1]

    def test_allocate_durations_weighted(self) -> None:
        assert _allocate_durations(100, [0.2, 0.6, 0.2]) == [20, 60, 20]

    def test_allocate_durations_single_stage(self) -> None:
        assert _allocate_durations(100, [1.0]) == [100]


class TestValidateAllocationInputs:
    def test_validate_allocation_inputs_valid(self) -> None:
        _validate_allocation_inputs(100, [1.0, 2.0, 3.0])

    def test_validate_allocation_inputs_zero_total_sec(self) -> None:
        with pytest.raises(ValueError, match="total_sec must be > 0"):
            _validate_allocation_inputs(0, [1.0, 2.0])

    def test_validate_allocation_inputs_negative_total_sec(self) -> None:
        with pytest.raises(ValueError, match="total_sec must be > 0"):
            _validate_allocation_inputs(-10, [1.0, 2.0])

    def test_validate_allocation_inputs_empty_weights(self) -> None:
        with pytest.raises(ValueError, match="weights must not be empty"):
            _validate_allocation_inputs(100, [])

    def test_validate_allocation_inputs_zero_weight(self) -> None:
        with pytest.raises(ValueError, match="all weights must be > 0"):
            _validate_allocation_inputs(100, [1.0, 0.0, 2.0])

    def test_validate_allocation_inputs_negative_weight(self) -> None:
        with pytest.raises(ValueError, match="all weights must be > 0"):
            _validate_allocation_inputs(100, [1.0, -1.0, 2.0])


class TestDistributePositiveDiff:
    def test_distribute_positive_diff_no_diff(self) -> None:
        """Test distribution when diff is 0."""
        raw = [10.3, 20.4, 30.5]
        base = [10, 20, 30]
        diff = 0

        _distribute_positive_diff(raw, base, diff)

        assert base == [10, 20, 30]

    def test_distribute_positive_diff_large_diff(self) -> None:
        """Test distribution when diff exceeds number of stages."""
        raw = [10.1, 20.2]
        base = [10, 20]
        diff = 5

        _distribute_positive_diff(raw, base, diff)

        assert base == [12, 23]


class TestDistributeNegativeDiff:
    def test_distribute_negative_diff_simple(self) -> None:
        raw = [10.3, 20.4, 30.5]
        base = [10, 20, 30]
        diff = -2

        _distribute_negative_diff(raw, base, diff)

        # Should subtract 1 from stages with lowest fractions: 10.3 and 20.4
        assert base == [9, 19, 30]

    def test_distribute_negative_diff_no_diff(self) -> None:
        raw = [10.3, 20.4, 30.5]
        base = [10, 20, 30]
        diff = 0

        _distribute_negative_diff(raw, base, diff)

        assert base == [10, 20, 30]

    def test_distribute_negative_diff_guard_limit(self) -> None:
        raw = [10.9, 20.9]
        base = [1, 1]
        diff = -100

        _distribute_negative_diff(raw, base, diff)

        assert base == [1, 1]
