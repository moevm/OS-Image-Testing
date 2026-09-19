import pytest

from imgtests.suites.drive.fio import (
    FioGrid,
    FioTiming,
    _timing,
)
from imgtests.suites.duration import (
    EIGHT_HOURS_SEC,
    FIVE_DAYS_SEC,
    FOUR_HOURS_SEC,
    ONE_DAY_SEC,
    TEN_DAYS_SEC,
)


@pytest.mark.parametrize(
    ("duration_sec", "expected"),
    [
        (
            3600,
            FioTiming(
                FioGrid((1,), (1,)),
                min_runtime_sec=10,
                log_avg_msec=1000,
                ramp_time_sec=1,
            ),
        ),
        (
            FOUR_HOURS_SEC,
            FioTiming(
                FioGrid((1, 4), (1,)),
                min_runtime_sec=30,
                log_avg_msec=1000,
                ramp_time_sec=5,
            ),
        ),
        (
            24400,
            FioTiming(
                FioGrid((1, 4), (1, 2)),
                min_runtime_sec=45,
                log_avg_msec=2000,
                ramp_time_sec=10,
            ),
        ),
        (
            EIGHT_HOURS_SEC,
            FioTiming(
                FioGrid((1, 4), (1, 2)),
                min_runtime_sec=45,
                log_avg_msec=2000,
                ramp_time_sec=10,
            ),
        ),
        (
            38800,
            FioTiming(
                FioGrid((1, 4, 8), (1, 2)),
                min_runtime_sec=60,
                log_avg_msec=3000,
                ramp_time_sec=15,
            ),
        ),
        (
            ONE_DAY_SEC,
            FioTiming(
                FioGrid((1, 4, 8), (1, 2)),
                min_runtime_sec=60,
                log_avg_msec=3000,
                ramp_time_sec=15,
            ),
        ),
        (
            96400,
            FioTiming(
                FioGrid((1, 2, 4, 8), (1, 2, 4)),
                min_runtime_sec=80,
                log_avg_msec=4000,
                ramp_time_sec=30,
            ),
        ),
        (
            FIVE_DAYS_SEC,
            FioTiming(
                FioGrid((1, 2, 4, 8), (1, 2, 4)),
                min_runtime_sec=80,
                log_avg_msec=4000,
                ramp_time_sec=30,
            ),
        ),
        (
            532000,
            FioTiming(
                FioGrid((1, 2, 4, 8, 16), (1, 2, 4, 8)),
                min_runtime_sec=100,
                log_avg_msec=5000,
                ramp_time_sec=60,
            ),
        ),
        (
            TEN_DAYS_SEC,
            FioTiming(
                FioGrid((1, 2, 4, 8, 16), (1, 2, 4, 8)),
                min_runtime_sec=100,
                log_avg_msec=5000,
                ramp_time_sec=60,
            ),
        ),
        (
            864001,
            FioTiming(
                FioGrid((1, 2, 4, 8, 16, 32), (1, 2, 4, 8)),
                min_runtime_sec=120,
                log_avg_msec=5000,
                ramp_time_sec=60,
            ),
        ),
    ],
    ids=[
        "Under 1 hour",
        "At 4h boundary",
        "4h-8h range",
        "At 8h boundary",
        "8h-1d range",
        "At 1d boundary",
        "1d-5d range",
        "At 5d boundary",
        "5d-10d range",
        "At 10d boundary",
        "Over 10 days",
    ],
)
def test_timing_returns_expected_config(
    duration_sec: int,
    expected: FioTiming,
) -> None:
    result = _timing(duration_sec)

    assert result == expected
