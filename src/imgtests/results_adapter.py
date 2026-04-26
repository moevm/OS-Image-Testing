from typing import Any, TypedDict


class AdapterResult(TypedDict):
    tool: str  # tool name
    test_type: dict[str, Any]  # test type or name info
    time: dict[str, Any]  # time-related values
    metrics: dict[str, Any]  # useful test metrics from the tool


def drop_json_fields(metrics: dict[str, Any], excluded_fields: list[str]) -> None:
    for key in excluded_fields:
        metrics.pop(key, None)
