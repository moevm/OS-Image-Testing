from typing import TYPE_CHECKING

import pytest

from imgtests.planning import AbstractRunnableManyTimesTest, AbstractRunnableTimeLimitedTest
from imgtests.suites.map import TestsRunnerConfig

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient
    from imgtests.types import TestResult


class MockManyTimesTest(AbstractRunnableManyTimesTest):
    """A concrete implementation of AbstractRunnableManyTimesTest for testing."""

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        iterations: int,
    ) -> Iterable[TestResult]:
        return iter([])


class MockTimeLimitedTest(AbstractRunnableTimeLimitedTest):
    """A concrete implementation of AbstractRunnableTimeLimitedTest for testing."""

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        return iter([])


class TestTestsRunnerConfigInit:
    """Tests for TestsRunnerConfig initialization."""

    def test_init_with_all_parameters(self) -> None:
        """Test initialization with all parameters provided."""
        tests = [MockManyTimesTest("desc", frozenset())]
        config = TestsRunnerConfig(
            description="Test suite",
            tests=tests,
            experiment_type="performance",
            duration=100,
            install_dependencies=True,
        )

        assert config.description == "Test suite"
        assert config.get_tests() is tests
        assert config.experiment_type == "performance"
        assert config.total_duration == 0
        assert config.install_dependencies is True
        assert config.test_duration == 0

    def test_init_without_install_dependencies(self) -> None:
        """Test initialization with default install_dependencies=False."""
        tests = [MockManyTimesTest("desc", frozenset())]
        config = TestsRunnerConfig(
            description="Test suite",
            tests=tests,
            experiment_type="endurance",
            duration=50,
        )

        assert config.install_dependencies is False


class TestTestsRunnerConfigTotalDuration:
    """Tests for the total_duration property."""

    def test_setter_updates_value(self) -> None:
        """Test that total_duration setter updates the value."""
        tests = [MockManyTimesTest("desc", frozenset())]
        config = TestsRunnerConfig(
            description="Test suite",
            tests=tests,
            experiment_type="performance",
            duration=100,
        )

        config.total_duration = 200

        assert config.total_duration == 0
        assert config.test_duration == 0

    def test_setter_calculates_test_duration_with_time_limited_tests(self) -> None:
        """Test that test_duration is calculated when time-limited tests are present."""
        config = TestsRunnerConfig(
            description="Test suite",
            tests=[
                MockManyTimesTest("many1", frozenset()),
                MockTimeLimitedTest,
                MockTimeLimitedTest,
            ],
            experiment_type="performance",
            duration=100,
        )

        # 2 time-limited tests, 100 // 2 = 50
        assert config.test_duration == 50
        assert config.total_duration == 100

    def test_setter_raises_value_error_when_not_enough_time(self) -> None:
        """Test that ValueError is raised when duration is less than time-limited tests count."""
        tests = [
            MockTimeLimitedTest,
            MockTimeLimitedTest,
            MockTimeLimitedTest,
        ]
        config = TestsRunnerConfig(
            description="Test suite",
            tests=tests,
            experiment_type="performance",
            duration=100,
        )

        with pytest.raises(
            ValueError,
            match=r"Each test cannot be run for less 1 second.*3 tests.*not enough",
        ):
            config.total_duration = 2

    def test_setter_raises_value_error_on_initialization(self) -> None:
        """Test that ValueError is raised during init when duration is not enough."""
        tests = [
            MockTimeLimitedTest,
            MockTimeLimitedTest,
        ]
        with pytest.raises(
            ValueError,
            match=r"Each test cannot be run for less 1 second.*1 seconds available, 2 tests.*",
        ):
            TestsRunnerConfig(
                description="Test suite",
                tests=tests,
                experiment_type="performance",
                duration=1,
            )

    def test_setter_does_not_raise_with_mixed_tests(self) -> None:
        """Test that only time-limited tests count toward the minimum duration check."""
        config = TestsRunnerConfig(
            description="Test suite",
            tests=[
                MockManyTimesTest("many1", frozenset()),
                MockManyTimesTest("many2", frozenset()),
                MockManyTimesTest("many3", frozenset()),
                MockTimeLimitedTest,
            ],
            experiment_type="performance",
            duration=1,
        )

        assert config.total_duration == 1
        assert config.test_duration == 1  # 1 time-limited test, 1 // 1 = 1


class TestTestsRunnerConfigTests:
    def test_reset_tests_reinit_timeouts(self) -> None:
        config = TestsRunnerConfig(
            description="Test suite",
            tests=[
                MockTimeLimitedTest,
                MockTimeLimitedTest,
            ],
            experiment_type="performance",
            duration=10,
        )

        assert config.total_duration == 10
        assert config.test_duration == 5

        config.set_tests(
            [
                MockTimeLimitedTest,
                MockTimeLimitedTest,
                MockTimeLimitedTest,
                MockTimeLimitedTest,
                MockTimeLimitedTest,
            ],
        )

        assert config.total_duration == 10
        assert config.test_duration == 2
