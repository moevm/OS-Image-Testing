import pytest

from imgtests.exec.loaders.perf import Perf, PerfBenchMetrics


@pytest.mark.parametrize(
    ("raw_metrics", "expected"),
    [
        (
            """# Running sched/messaging benchmark...
            # 20 sender and receiver processes per group
            # 10 groups == 400 processes run

                 Total time: 0.464 [sec]

            # Running sched/pipe benchmark...
            # Executed 1000000 pipe operations between two processes

                 Total time: 7.685 [sec]

                   7.685049 usecs/op
                     130122 ops/sec

            # Running sched/seccomp-notify benchmark...
            # Executed 1000000 system calls

                 Total time: 9.110 [sec]

                   9.110067 usecs/op
                     109768 ops/sec
            """,
            (
                PerfBenchMetrics(
                    benchmark="sched/messaging",
                    total_time=0.464,
                ),
                PerfBenchMetrics(
                    benchmark="sched/pipe",
                    total_time=7.685,
                    usecs_per_op=7.685049,
                    ops_per_sec=130122,
                ),
                PerfBenchMetrics(
                    benchmark="sched/seccomp-notify",
                    total_time=9.11,
                    usecs_per_op=9.110067,
                    ops_per_sec=109768,
                ),
            ),
        ),
        (
            """# Running syscall/basic benchmark...
            # Executed 10,000,000 getppid() calls
                 Total time: 4.264 [sec]

                   0.426443 usecs/op
                  2,344,982 ops/sec

            # Running syscall/getpgid benchmark...
            # Executed 10,000,000 getpgid() calls
                 Total time: 3.760 [sec]

                   0.376017 usecs/op
                  2,659,456 ops/sec

            # Running syscall/fork benchmark...
            # Executed 10,000 fork() calls
                 Total time: 58.884 [sec]

                5888.403000 usecs/op
                        169 ops/sec

            # Running syscall/execve benchmark...
            # Executed 10,000 execve() calls
                 Total time: 26.450 [sec]

                2645.092600 usecs/op
                        378 ops/sec
            """,
            (
                PerfBenchMetrics(
                    benchmark="syscall/basic",
                    total_time=4.264,
                    usecs_per_op=0.426443,
                    ops_per_sec=982,
                ),
                PerfBenchMetrics(
                    benchmark="syscall/getpgid",
                    total_time=3.76,
                    usecs_per_op=0.376017,
                    ops_per_sec=456,
                ),
                PerfBenchMetrics(
                    benchmark="syscall/fork",
                    total_time=58.884,
                    usecs_per_op=5888.403,
                    ops_per_sec=169,
                ),
                PerfBenchMetrics(
                    benchmark="syscall/execve",
                    total_time=26.45,
                    usecs_per_op=2645.0926,
                    ops_per_sec=378,
                ),
            ),
        ),
        (
            """perf bench mem memcpy
            # Running 'mem/memcpy' benchmark:
            # function 'default' (Default memcpy() provided by glibc)
            # Copying 1MB bytes ...

                6,180775 GB/sec
            # function 'x86-64-unrolled' (unrolled memcpy() in arch/x86/lib/memcpy_64.S)
            # Copying 1MB bytes ...

                1,337757 GB/sec
            # function 'x86-64-movsq' (movsq-based memcpy() in arch/x86/lib/memcpy_64.S)
            # Copying 1MB bytes ...

                7,025629 GB/sec
            """,
            (
                PerfBenchMetrics(
                    benchmark="mem/memcpy",
                    gb_per_sec_default=6.180775,
                    gb_per_sec_unrolled=1.337757,
                    gb_per_sec_movsq_based=7.025629,
                ),
            ),
        ),
        (
            """
            # Running 'mem/memset' benchmark:
            # function 'default' (Default memset() provided by glibc)
            # Copying 1MB bytes ...

                21,229620 GB/sec
            # function 'x86-64-unrolled' (unrolled memset() in arch/x86/lib/memset_64.S)
            # Copying 1MB bytes ...

                21,701389 GB/sec
            # function 'x86-64-stosq' (movsq-based memset() in arch/x86/lib/memset_64.S)
            # Copying 1MB bytes ...

                30,517578 GB/sec
            """,
            (
                PerfBenchMetrics(
                    benchmark="mem/memset",
                    gb_per_sec_default=21.229620,
                    gb_per_sec_unrolled=21.701389,
                    gb_per_sec_movsq_based=30.517578,
                ),
            ),
        ),
        ("", ()),
    ],
    ids=[
        "'perf sched all' parsing",
        "'perf syscall all' parsing",
        "'perf mem memcpy' parsing",
        "'perf mem memset' parsing",
        "Empty output",
    ],
)
def test_parse_metrics(raw_metrics: str, expected: tuple[PerfBenchMetrics, ...]) -> None:
    result = Perf.parse_bench(raw_metrics)
    assert result == expected


@pytest.mark.parametrize(
    ("metrics", "expected"),
    [
        (
            (
                PerfBenchMetrics(
                    benchmark="mem/memset",
                    gb_per_sec_default=21.229620,
                    gb_per_sec_unrolled=21.701389,
                    gb_per_sec_movsq_based=30.517578,
                ),
            ),
            '[{"benchmark": "mem/memset", "gb_per_sec_default": 21.22962, '
            '"gb_per_sec_unrolled": 21.701389, '
            '"gb_per_sec_movsq_based": 30.517578}]',
        ),
        (
            (
                PerfBenchMetrics(
                    benchmark="mem/memset",
                    gb_per_sec_default=21.229620,
                    gb_per_sec_unrolled=21.701389,
                    gb_per_sec_movsq_based=30.517578,
                    total_time=3.2,
                    ops_per_sec=23211,
                    usecs_per_op=23996.39934,
                ),
            ),
            '[{"benchmark": "mem/memset", "total_time": 3.2, '
            '"usecs_per_op": 23996.39934, "ops_per_sec": 23211, '
            '"gb_per_sec_default": 21.22962, '
            '"gb_per_sec_unrolled": 21.701389, '
            '"gb_per_sec_movsq_based": 30.517578}]',
        ),
        ((), "[]"),
    ],
    ids=[
        "With None values",
        "Without None values",
        "Empty metrics",
    ],
)
def test_serialize_metrics(metrics: tuple[PerfBenchMetrics, ...], expected: str) -> None:
    result = Perf.serialize_metrics(metrics)
    assert result == expected
