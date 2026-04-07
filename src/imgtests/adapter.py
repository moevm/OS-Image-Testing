from typing import Any


class ResultAdapter:
    def __init__(self, tool: str) -> None:
        self.tool = tool

    def __call__(self, raw_result: dict[str, Any], test_index: int = 0) -> dict[str, Any]:
        return {"tool": self.tool, **self.split_result(raw_result, test_index)}

    def split_result(
        self,
        raw_result: dict[str, Any],
        test_index: int = 0,  # noqa: ARG002
    ) -> dict[str, Any]:
        return {
            "time": raw_result.get("time", {}),
            "metrics": raw_result.get("metrics", raw_result),
            "summary": raw_result.get("summary", {}),
        }

    def drop_fields(
        self,
        metrics: dict[str, Any],
        excluded_fields: list[str],
    ) -> dict[str, Any]:
        for key in excluded_fields:
            metrics.pop(key, None)
        return metrics
