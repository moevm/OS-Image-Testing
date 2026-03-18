from __future__ import annotations


def parse_size_to_bytes(value: str) -> int | None:
    normalized = str(value).strip()
    if not normalized or normalized.endswith("%"):
        return None

    multiplier = 1
    suffix = normalized[-1].lower()
    number = normalized

    if suffix in {"k", "m", "g", "t"}:
        number = normalized[:-1]
        if suffix == "k":
            multiplier = 1024
        elif suffix == "m":
            multiplier = 1024**2
        elif suffix == "g":
            multiplier = 1024**3
        elif suffix == "t":
            multiplier = 1024**4

    try:
        return int(float(number) * multiplier)
    except (TypeError, ValueError):
        return None


def bytes_to_mib_str(size_bytes: int) -> str:
    mib = max(1, size_bytes // (1024**2))
    return f"{mib}M"
