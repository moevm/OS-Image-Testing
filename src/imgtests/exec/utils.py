import re
from enum import Enum
from typing import Any

from imgtests.constant import VER_PATTERN
from imgtests.types import Version


def create_opt(key: str, value: Any | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, bool):
        return [f"--{key}"] if value else []
    if isinstance(value, Enum):
        return [f"--{key}", str(value.value)]
    return [f"--{key}", str(value)]


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
