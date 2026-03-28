from __future__ import annotations

import re

_SIZE_RE = re.compile(r"^(?P<number>\d+(?:\.\d+)?)(?P<suffix>[kKmMgGtT]?)$")


def parse_size_to_bytes(value: str) -> int | None:
    normalized = str(value).strip()
    if not normalized:
        return None

    if _SIZE_RE.fullmatch(normalized) is None:
        err_msg = f"Invalid size value '{value}'."
        raise ValueError(err_msg)

    suffix = normalized[-1].lower()
    match suffix:
        case "k":
            multiplier = 1024
            number = normalized[:-1]
        case "m":
            multiplier = 1024**2
            number = normalized[:-1]
        case "g":
            multiplier = 1024**3
            number = normalized[:-1]
        case "t":
            multiplier = 1024**4
            number = normalized[:-1]
        case _:
            multiplier = 1
            number = normalized

    try:
        return int(float(number) * multiplier)
    except (TypeError, ValueError) as exc:
        err_msg = f"Invalid size value '{value}'."
        raise ValueError(err_msg) from exc


def bytes_to_mib_str(size_bytes: int) -> str:
    mib = max(1, size_bytes // (1024**2))
    return f"{mib}MiB"
