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
        (
            dedent(
                """\
            stress-ng: info:  [14018] syscall: Top 268 fastest system calls (timings in nanosecs):
            stress-ng: info:  [14018] syscall:               System Call   Avg (ns)   Min (ns)
            stress-ng: info:  [14018] syscall:                      time     2430.0       2430
            stress-ng: info:  [14018] syscall:                    getpid     2805.0       2720
            stress-ng: info:  [14018] syscall:           restart_syscall     3305.0       3270
            stress-ng: info:  [14018] syscall:    sched_get_priority_min     3365.0       3090
            stress-ng: info:  [14018] syscall:             clock_gettime     3400.0       3080
            stress-ng: info:  [14018] syscall:           set_robust_list     3825.0       3050
            stress-ng: info:  [14018] syscall:              timer_delete     4200.0       4150
            stress-ng: info:  [14018] syscall:    sched_get_priority_max     4495.0       3900
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
                    None,
                    (
                        StressNGSyscallTiming("sched_get_priority_max", 4495.0, 3900, -1),
                        StressNGSyscallTiming("timer_delete", 4200.0, 4150, -1),
                        StressNGSyscallTiming("set_robust_list", 3825.0, 3050, -1),
                        StressNGSyscallTiming("clock_gettime", 3400.0, 3080, -1),
                        StressNGSyscallTiming("sched_get_priority_min", 3365.0, 3090, -1),
                        StressNGSyscallTiming("restart_syscall", 3305.0, 3270, -1),
                        StressNGSyscallTiming("getpid", 2805.0, 2720, -1),
                        StressNGSyscallTiming("time", 2430.0, 2430, -1),
                    ),
                ),
            ],
        ),
        (
            dedent(
                """\
        stress-ng: info:  [667] syscall: Top 263 fastest system calls (timings in nanosecs):
        stress-ng: info:  [667] syscall:               System Call   Avg (ns)   Min (ns)   Max (ns)
        stress-ng: info:  [667] syscall:                      time     8717.5       1914      15521
        stress-ng: info:  [667] syscall:              gettimeofday    12214.0       2055      22373
        stress-ng: info:  [667] syscall:                 setresgid    19381.5      18801      19962
        stress-ng: info:  [667] syscall:                 setresuid    20068.0      18851      21285
        stress-ng: info:  [667] syscall:                     fcntl    20908.0      19998      21818
        stress-ng: info:  [667] syscall:                    getsid    23327.5      22468      24187
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
                    None,
                    (
                        StressNGSyscallTiming("getsid", 23327.5, 22468, 24187),
                        StressNGSyscallTiming("fcntl", 20908.0, 19998, 21818),
                        StressNGSyscallTiming("setresuid", 20068.0, 18851, 21285),
                        StressNGSyscallTiming("setresgid", 19381.5, 18801, 19962),
                        StressNGSyscallTiming("gettimeofday", 12214.0, 2055, 22373),
                        StressNGSyscallTiming("time", 8717.5, 1914, 15521),
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
        "Syscall with syscall-top and perf entries.",
        "Metrics for different subsystems.",
        "OpenSUSE slowest syscall parse: no max value os suse.",
        "Poky slowest syscall parse.",
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
