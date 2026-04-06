from typing import Any


class ResultAdapter:
    def __init__(self) -> None:
        self.tool = ""

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


class StressNgAdapter(ResultAdapter):
    def __init__(self) -> None:
        self.tool = "stress-ng"

    def split_result(self, raw_result: dict[str, Any], test_index: int = 0) -> dict[str, Any]:
        metrics = raw_result.get("stress_ng_metrics", [])
        if not metrics:
            return {
                "test_type": "",
                "time": {},
                "metrics": {},
                "summary": raw_result.get("stress_ng_summary", {}),
            }

        test_metrics = metrics[test_index]
        test_type = {"stressor": test_metrics.get("stressor", "")}
        time = {
            "real_time_secs": test_metrics.get("real_time_secs", 0),
            "usr_time_secs": test_metrics.get("usr_time_secs", 0),
            "sys_time_secs": test_metrics.get("sys_time_secs", 0),
        }

        excluded_fields = [*test_type.keys(), *time.keys()]
        test_metrics = self.drop_fields(test_metrics, excluded_fields)

        summary = raw_result.get("stress_ng_summary", {})
        return {
            "test_type": test_type,
            "time": time,
            "metrics": test_metrics,
            "summary": summary,
        }


class PerfAdapter(ResultAdapter):
    def __init__(self) -> None:
        self.tool = "perf"

    def split_result(self, raw_result: dict[str, Any], test_index: int = 0) -> dict[str, Any]:
        metrics = raw_result[test_index]
        test_type = {"benchmark": metrics.get("benchmark", "")}
        time = {"total_time": metrics.get("total_time", 0)}

        excluded_fields = [*test_type.keys(), *time.keys()]
        metrics = self.drop_fields(metrics, excluded_fields)

        return {
            "test_type": test_type,
            "time": time,
            "metrics": metrics,
            "summary": {},
        }


class IPerfAdapter(ResultAdapter):
    def __init__(self) -> None:
        self.tool = "iperf3"

    def split_result(
        self,
        raw_result: dict[str, Any],
        test_index: int = 0,  # noqa: ARG002
    ) -> dict[str, Any]:
        client_metrics = raw_result.get("client", {})
        server_metrics = raw_result.get("server", {})
        test_info = client_metrics.get("start", {}).get("test_start", {})
        client_results = client_metrics.get("end", {})
        server_results = server_metrics.get("end", {})

        test_type = {"protocol": test_info.get("protocol", "")}
        time = {"duration_sec": float(test_info.get("duration", 0.0))}

        metrics = {
            "client": {
                "sum_sent": client_results.get("sum_sent", {}),
                "sum_received": client_results.get("sum_received", {}),
                "cpu_utilization_percent": client_results.get("cpu_utilization_percent", {}),
            },
            "server": {
                "sum_sent": server_results.get("sum_sent", {}),
                "sum_received": server_results.get("sum_received", {}),
                "cpu_utilization_percent": server_results.get("cpu_utilization_percent", {}),
            },
        }

        return {
            "test_type": test_type,
            "time": time,
            "metrics": metrics,
            "summary": {},
        }


class PTSAdapter(ResultAdapter):
    def __init__(self) -> None:
        self.tool = "pts"

    def split_result(self, raw_result: dict[str, Any], test_index: int = 0) -> dict[str, Any]:
        system_info = raw_result.get("systems", {})
        system_info = system_info.get(next(iter(system_info.keys())), {})

        test_results = raw_result.get("results", {})
        test_results = test_results.get(list(test_results.keys())[test_index], {})

        test_metrics = test_results.get("results", {})
        test_metrics = test_metrics.get(next(iter(test_metrics.keys())), {})
        test_metrics = self.drop_fields(test_metrics, ["details"])

        test_type = {
            "identifier": test_results.get("identifier", ""),
            "title": test_results.get("title", ""),
            "description": test_results.get("description", ""),
        }
        time = {
            "timestamp": system_info.get("timestamp", ""),
        }

        return {
            "test_type": test_type,
            "time": time,
            "metrics": test_metrics,
            "summary": {},
        }
