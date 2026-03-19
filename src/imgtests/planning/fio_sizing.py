from __future__ import annotations


def parse_size_to_bytes(value: str) -> int | None:
    normalized = str(value).strip()
    if not normalized or normalized.endswith("%"):
        return None

    suffix = normalized[-1].lower()
    match suffix:
        case "k":
            multiplier = 1024
        case "m":
            multiplier = 1024**2
        case "g":
            multiplier = 1024**3
        case "t":
            multiplier = 1024**4
        case _:
            multiplier = 1
    number = normalized[:-1]

    try:
        return int(float(number) * multiplier)
    except (TypeError, ValueError):
        return None


def bytes_to_mib_str(size_bytes: int) -> str:
    mib = max(1, size_bytes // (1024**2))
    return f"{mib}M"
