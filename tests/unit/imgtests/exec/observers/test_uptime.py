from datetime import datetime

import pytest

from imgtests.exec.observers.uptime import LoadAverage, Uptime, UptimeInfo


@pytest.mark.parametrize(
    ("raw_uptime", "result"),
    [
        (
            " 00:35:26 up  9:59,  1 user,  load average: 7.64, 6.85, 6.45",
            UptimeInfo(
                curent_time=datetime.strptime("00:35:26", "%H:%M:%S").astimezone(),
                uptime="9:59",
                users=1,
                load_avg=LoadAverage(7.64, 6.85, 6.45),
            ),
        ),
        (
            " 21:35:21 up 18 min,  3 users,  load average: 0.00, 0.00, 0.00",
            UptimeInfo(
                curent_time=datetime.strptime("21:35:21", "%H:%M:%S").astimezone(),
                uptime="18 min",
                users=3,
                load_avg=LoadAverage(0.00, 0.00, 0.00),
            ),
        ),
    ],
)
def test_parse_uptime(raw_uptime: str, result: UptimeInfo) -> None:
    assert Uptime.parse_uptime(raw_uptime) == result
