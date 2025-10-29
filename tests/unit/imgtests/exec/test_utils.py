from enum import Enum
from typing import Any

import pytest

from imgtests.exec.utils import add_flag, create_opt


class TEnum(Enum):
    VALUE1 = "value1"
    VALUE2 = 2


@pytest.mark.parametrize(
    ("key", "value", "expected"),
    [
        ("", None, []),
        ("flag", True, ["--flag"]),
        ("flag", False, []),
        ("str", "text", ["--str", "text"]),
        ("int", 42, ["--int", "42"]),
        ("float", 3.14, ["--float", "3.14"]),
        ("enumval1", TEnum.VALUE1, ["--enumval1", "value1"]),
        ("enumval2", TEnum.VALUE2, ["--enumval2", "2"]),
    ],
)
def test_create_opt(key: str, value: Any | None, expected: list[str]) -> None:
    result = create_opt(key, value)
    assert result == expected


def test_add_flag() -> None:
    result = add_flag("flag")
    assert result == ["--flag"]
