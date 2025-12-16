import pytest

from imgtests.exec.loaders.stress_ng import StressNg, StressNGMetrics


@pytest.mark.parametrize(
    ("raw_metrics", "expected"),
    [
        (
            "stress-ng: info: [12345] cpu 123456 10.50 8.20 2.30 11757.71 11834.15 105.00",
            [StressNGMetrics("cpu", 123456, 10.50, 8.20, 2.30, 11757.71, 11834.15, 105.00)],
        ),
        (
            """stress-ng: info:  [7645] cpu  2493  2.10  1.00  0.70  140.29  16.03  98.90
stress-ng: info:  [7645] vm  2283  2.00  1.98  0.00  1140.30  1153.03  98.90""",
            [
                StressNGMetrics("cpu", 2493, 2.1, 1, 0.7, 140.29, 16.03, 98.9),
                StressNGMetrics("vm", 2283, 2, 1.98, 0, 1140.3, 1153.03, 98.9),
            ],
        ),
        ("stress-ng: info: [12345] cpu 123456 10.50 8.20 2.30 11757.71 11834.15", []),
        ("", []),
        ("stress-ng: info: [12345] cpu 123456.7 10.50 8.20 2.30 11757.71 11834.15 105.00", []),
        (
            "stress-ng: metrc: [635] cpu  692  10.03  10.00  0.03  69.00  69.03  99.96  6200",
            [StressNGMetrics("cpu", 692, 10.03, 10.00, 0.03, 69.00, 69.03, 99.96, 6200)],
        ),
        (
            """stress-ng: metrc: [635] cpu  692  10.03  10.00  0.03  69.00  69.03  99.96  6200
stress-ng: metrc: [635] vm  0  10.01  0.07  0.15  0.00  0.00  2.26  2236""",
            [
                StressNGMetrics("cpu", 692, 10.03, 10.00, 0.03, 69.00, 69.03, 99.96, 6200),
                StressNGMetrics("vm", 0, 10.01, 0.07, 0.15, 0, 0, 2.26, 2236),
            ],
        ),
    ],
    ids=[
        "One stressor with old metrics format.",
        "Two stressors with old metrics format.",
        "Less fields then required.",
        "Empty output.",
        "Invalid bogo opts format.",
        "One stressor with new metrics format.",
        "Two stressors with new metrics format.",
    ],
)
def test_parse_metrics(raw_metrics: str, expected: list[StressNGMetrics]) -> None:
    result = StressNg.parse_metrics(raw_metrics)
    assert result == expected
