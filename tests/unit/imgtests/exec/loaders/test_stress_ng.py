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
                stress-ng: info: [999] 5000000000 CPU Clock 0.500 B/sec
                stress-ng: info: [999] 0 Page Faults Major 0.000 /sec
                stress-ng: info: [999] 7712 Kmalloc 1.518 K/sec
                stress-ng: info: [999] 262,244 RCU Utilization 3.809 K/sec
                stress-ng: info: [999] 3,742,640,922 Cache Misses 54.365 M/sec ( 1.572%)
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
                    {
                        "cpu_clock": 5000000000,
                        "page_faults_major": 0,
                        "kmalloc": 7712,
                        "rcu_utilization": 262244,
                        "cache_misses": 3742640922,
                    },
                    (
                        StressNGSyscallTiming("open", 9.0, 1, 10),
                        StressNGSyscallTiming("read", 7.0, 1, 10),
                        StressNGSyscallTiming("close", 2.0, 1, 10),
                    ),
                ),
            ],
        ),
        (
            dedent(
                """\
                stress-ng: info:  [999] syscall:
                stress-ng: info:  [999]              4,658,202,225 CPU Cycles 67.665 M/sec
                stress-ng: info:  [999]              4,330,169,695 Instructions 62.900 M/sec
                stress-ng: info:  [999] hdd:
                stress-ng: info:  [999]             21,900,101,550 CPU Cycles 0.318 B/sec
                stress-ng: info:  [999]             34,961,558,984 Instructions 0.508 B/sec
                """,
            ).strip(),
            [
                StressNGMetrics(
                    "syscall",
                    0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    None,
                    {
                        "cpu_cycles": 4658202225,
                        "instructions": 4330169695,
                    },
                    None,
                ),
                StressNGMetrics(
                    "hdd",
                    0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    None,
                    {
                        "cpu_cycles": 21900101550,
                        "instructions": 34961558984,
                    },
                    None,
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
        "Syscall with syscall-top and perf entries.",
        "Metrics for different subsystems.",
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
