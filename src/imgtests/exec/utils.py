from enum import Enum
from typing import Any


def create_opt(key: str, value: Any | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, bool):
        return [f"--{key}"] if value else []
    if isinstance(value, Enum):
        return [f"--{key}", str(value.value)]
    return [f"--{key}", str(value)]
