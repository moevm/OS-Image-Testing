import pytest

from imgtests.exec.observers.journalctl import Journalctl


@pytest.mark.parametrize(
    ("line", "result"),
    [
        (
            "2026-03-04 12:45:12",
            True,
        ),
        (
            "2026-05-04 18:45:12",
            True,
        ),
        (
            "2026-43-04 12:65:12",
            False,
        ),
        (
            "2024-30-11 21:45:12",
            False,
        ),
    ],
)
def test_parse_time(line: str, result: bool):
    assert Journalctl._validate_time(line) == result  # noqa: SLF001
