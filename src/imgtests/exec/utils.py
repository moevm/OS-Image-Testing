from enum import Enum
from typing import Any


def create_opt(key: str, value: Any | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, Enum):
        return [f"--{key}", str(value.value)]
    return [f"--{key}", str(value)]
