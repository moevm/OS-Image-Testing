import pytest

from imgtests.exec.observers.systemd_analyze import SystemdAnalyze


@pytest.mark.parametrize(
    ("raw_line", "result"),
    [
        (
            "Startup finished in "
            "6.043s (kernel) + 41.054s (initrd) + 1min 27.366s (userspace) = 2min 14.464s \n"
            "graphical.target reached after 1min 19.437s in userspace.",
            {
                "kernel_time": 6.043,
                "initrd_time": 41.054,
                "userspace_time": 87.366,
                "total_time": 134.464,
            },
        ),
        (
            "Startup finished in "
            "15.476s (firmware) + 20.245s (loader) + 8.919s (kernel) "
            "+ 1min 54.925s (userspace) = 2min 39.567s \n"
            "graphical.target reached after 1min 54.873s in userspace.",
            {
                "firmware": 15.476,
                "loader": 20.245,
                "kernel": 8.919,
                "userspace": 114.925,
                "total_time": 159.567,
            },
        ),
        (
            "Startup finished in "
            "7.995s (kernel) + 30.906s (initrd) + 2min 36.845s (userspace) = 3min 15.747s \n"
            "graphical.target reached after 1min 54.873s in userspace.",
            {
                "kernel_time": 7.995,
                "initrd_time": 30.906,
                "userspace_time": 156.845,
                "total_time": 195.747,
            },
        ),
    ],
)
def test_parse_time(raw_line: str, result: dict[str, float]):
    sa = SystemdAnalyze()
    assert SystemdAnalyze._parse_time(raw_line) == result
