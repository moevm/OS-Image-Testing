from enum import Enum
from typing import Any

import pytest

from imgtests.exec.utils import add_flag, create_opt, extract_version, kwargs_to_cmd_args
from imgtests.types import Version


class TEnum(Enum):
    VALUE1 = "value1"
    VALUE2 = 2


@pytest.mark.parametrize(
    ("key", "value", "use_equals", "expected"),
    [
        ("", None, False, []),
        ("flag", True, False, ["--flag"]),
        ("flag", False, False, []),
        ("str", "text", True, ["--str=text"]),
        ("int", 42, True, ["--int=42"]),
        ("float", 3.14, False, ["--float", "3.14"]),
        ("enumval1", TEnum.VALUE1, True, ["--enumval1=value1"]),
        ("enumval2", TEnum.VALUE2, False, ["--enumval2", "2"]),
    ],
)
def test_create_opt(key: str, value: Any | None, expected: list[str], use_equals: bool) -> None:
    result = create_opt(key, value, use_equals=use_equals)
    assert result == expected


def test_add_flag() -> None:
    result = add_flag("flag")
    assert result == ["--flag"]


@pytest.mark.parametrize(
    ("out", "version"),
    [
        ("kirk, 2.3", Version("2.3")),
        (
            "stress-ng, version 0.17.06 (gcc 13.2.0, x86_64 Linux 6.14.0-29-generic)",
            Version("0.17.06"),
        ),
        ("fio-3.36", Version("3.36")),
        ("perf version 6.12.47", Version("6.12.47")),
        ("Phoronix Test Suite v10.8.4", Version("10.8.4")),
    ],
)
def test_extract_version(out: str, version: str) -> None:
    result = extract_version(out)
    assert result == version


@pytest.mark.parametrize(
    ("kwargs", "command"),
    [
        (
            {"name": "test", "numjobs": 2, "size": "4096B", "output-format": "json"},
            ["--name", "test", "--numjobs", "2", "--size", "4096B", "--output-format", "json"],
        ),
        (
            {"cpu": 2, "cpu-method": "crc16", "timeout": 10, "metrics": True},
            ["--cpu", "2", "--cpu-method", "crc16", "--timeout", "10", "--metrics"],
        ),
        ({}, []),
    ],
)
def test_kwargs_to_cmd_args(kwargs: dict[str, Any], command: list[str]) -> None:
    result = kwargs_to_cmd_args(**kwargs)
    assert result == command
