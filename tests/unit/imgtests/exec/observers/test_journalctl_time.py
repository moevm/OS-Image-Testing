from contextlib import nullcontext as does_not_raise

import pytest

from imgtests.exec.observers.journalctl import Journalctl


@pytest.mark.parametrize(
    ("date", "expectation"),
    [
        (
            "2026-03-04 12:45:12",
            does_not_raise(),
        ),
        (
            "2026-05-04 18:45:12",
            does_not_raise(),
        ),
        (
            "today",
            does_not_raise(),
        ),
        (
            "yesterday",
            does_not_raise(),
        ),
        (
            "tomorrow",
            does_not_raise(),
        ),
        (
            "2026-43-04 12:65:12",
            pytest.raises(ValueError),  # noqa: PT011
        ),
        (
            "2024-30-11 21:45:12",
            pytest.raises(ValueError),  # noqa: PT011
        ),
    ],
)
def test_parse_time(date: str, expectation: bool) -> None:
    with expectation:
        Journalctl._check_journalctl_date_format(date)  # noqa: SLF001
