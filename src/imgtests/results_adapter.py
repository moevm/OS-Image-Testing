from abc import ABC, abstractmethod
from typing import Any, TypedDict


class AdapterResult(TypedDict):
    tool: str  # tool name
    test_type: dict[str, Any]  # test type or name info
    time: dict[str, Any]  # time-related values
    metrics: dict[str, Any]  # useful test metrics from the tool
    summary: dict[str, Any]  # stats summary of the test results


class JSONAdapter(ABC):
    def __init__(self, tool: str) -> None:
        self.tool = tool

    def __call__(self, raw_metrics: dict[str, Any], test_index: int = 0) -> dict[str, Any]:
        return AdapterResult(
            tool=self.tool,
            **self.split_result(raw_metrics, test_index),
        )

    @abstractmethod
    def split_result(
        self,
        metrics: dict[str, Any],
        test_index: int = 0,
    ) -> dict[str, Any]:
        pass

    def drop_fields(
        self,
        metrics: dict[str, Any],
        excluded_fields: list[str],
    ) -> dict[str, Any]:
        for key in excluded_fields:
            metrics.pop(key, None)
        return metrics
