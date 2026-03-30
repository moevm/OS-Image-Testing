from dataclasses import dataclass


@dataclass(frozen=True)
class MetricSample:
    stage_name: str
    subsystem: str
    metric_name: str
    value: float
