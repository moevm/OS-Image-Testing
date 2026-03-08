from enum import Enum
from typing import TYPE_CHECKING, Any

from imgtests.constant import VER_PATTERN
from imgtests.types import Version

if TYPE_CHECKING:
    import re


def create_opt(key: str, value: Any | None, use_equals: bool = False) -> list[str]:
    if value is None:
        return []
    if isinstance(value, bool):
        return [f"--{key}"] if value else []
    value_str = str(value.value) if isinstance(value, Enum) else str(value)

    if use_equals:
        return [f"--{key}={value_str}"]
    return [f"--{key}", value_str]


def add_flag(key: str) -> list[str]:
    return create_opt(key=key, value=True)


def extract_version(out: str, pattern: re.Pattern[str] = VER_PATTERN) -> Version | None:
    match = pattern.search(out)
    if match is None:
        return None
    return Version(match.group())


def kwargs_to_cmd_args(**kwargs: dict[str, Any]) -> list[str]:
    args: list[str] = []
    for k, w in kwargs.items():
        args.extend(create_opt(k, w))
    return args
