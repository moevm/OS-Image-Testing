from textwrap import dedent

import pytest

from imgtests.exec.loaders.stress_ng import StressNg, StressNGMetrics, StressNGSyscallTiming


@pytest.mark.parametrize(
    ("raw_metrics", "expected"),
    [
        (
            "stress-ng: info: [12345] cpu 123456 10.50 8.20 2.30 11757.71 11834.15 105.00",
            [StressNGMetrics("cpu", 123456, 10.50, 8.20, 2.30, 11757.71, 11834.15, 105.00)],
        ),
        (
            dedent(
                """\
                stress-ng: info:  [7645] cpu  2493  2.10  1.00  0.70  140.29  16.03  98.90
                stress-ng: info:  [7645] vm  2283  2.00  1.98  0.00  1140.30  1153.03  98.90
                """,
            ).strip(),
            [
                StressNGMetrics("cpu", 2493, 2.10, 1.00, 0.70, 140.29, 16.03, 98.90),
                StressNGMetrics("vm", 2283, 2.00, 1.98, 0.00, 1140.30, 1153.03, 98.90),
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
            dedent(
                """\
                stress-ng: metrc: [635] cpu  692  10.03  10.00  0.03  69.00  69.03  99.96  6200
                stress-ng: metrc: [635] vm  0  10.01  0.07  0.15  0.00  0.00  2.26  2236
                """,
            ).strip(),
            [
                StressNGMetrics("cpu", 692, 10.03, 10.00, 0.03, 69.00, 69.03, 99.96, 6200),
                StressNGMetrics("vm", 0, 10.01, 0.07, 0.15, 0.00, 0.00, 2.26, 2236),
            ],
        ),
        (
            dedent(
                """\
                stress-ng: metrc: [999] syscall  1  1.00  0.50  0.50  1.00  1.00  50.00
                stress-ng: metrc: [999] syscall: open   9.0  1  10
                stress-ng: metrc: [999] syscall: close  2.0  1  10
                stress-ng: metrc: [999] syscall: read   7.0  1  10
                """,
            ).strip(),
            [
                StressNGMetrics(
                    "syscall",
                    1,
                    1.00,
                    0.50,
                    0.50,
                    1.00,
                    1.00,
                    50.00,
                    None,
                    (
                        StressNGSyscallTiming("open", 9.0, 1, 10),
                        StressNGSyscallTiming("read", 7.0, 1, 10),
                        StressNGSyscallTiming("close", 2.0, 1, 10),
                    ),
                ),
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
        "Syscall with syscall-top entries.",
    ],
)
def test_parse_metrics(raw_metrics: str, expected: list[StressNGMetrics]) -> None:
    metrics, summary = StressNg.parse_metrics(raw_metrics)
    assert metrics == expected
    assert summary is None


def test_parse_metrics_syscall_top10_slowest_selects_10_slowest() -> None:
    raw_metrics = dedent(
        """\
        stress-ng: metrc: [999] syscall  1  1.00  0.50  0.50  1.00  1.00  50.00
        stress-ng: metrc: [999] syscall: s00  0.5  1  10
        stress-ng: metrc: [999] syscall: s01  1.0  1  10
        stress-ng: metrc: [999] syscall: s02  2.0  1  10
        stress-ng: metrc: [999] syscall: s03  3.0  1  10
        stress-ng: metrc: [999] syscall: s04  4.0  1  10
        stress-ng: metrc: [999] syscall: s05  5.0  1  10
        stress-ng: metrc: [999] syscall: s06  6.0  1  10
        stress-ng: metrc: [999] syscall: s07  7.0  1  10
        stress-ng: metrc: [999] syscall: s08  8.0  1  10
        stress-ng: metrc: [999] syscall: s09  9.0  1  10
        stress-ng: metrc: [999] syscall: s10  10.0  1  20
        stress-ng: metrc: [999] syscall: s11  11.0  1  20
        stress-ng: metrc: [999] syscall: s12  12.0  1  20
        stress-ng: metrc: [999] syscall: s13  13.0  1  20
        stress-ng: metrc: [999] syscall: s14  14.0  1  20
        stress-ng: metrc: [999] syscall: s15  15.0  1  20
        """,
    ).strip()

    metrics, summary = StressNg.parse_metrics(raw_metrics)
    assert summary is None

    syscall_metrics = [m for m in metrics if m.stressor == "syscall"]
    assert syscall_metrics, "No syscall metrics parsed"

    top10 = syscall_metrics[0].top10_slowest
    assert top10 is not None, "top10_slowest must not be None for syscall"
    names = [t.name for t in top10]
    assert names == ["s15", "s14", "s13", "s12", "s11", "s10", "s09", "s08", "s07", "s06"]

    avgs = [t.avg_ns for t in top10]
    assert avgs == sorted(avgs, reverse=True), f"Not sorted desc by avg_ns: {avgs}"
