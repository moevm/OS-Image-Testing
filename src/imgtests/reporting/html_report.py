from __future__ import annotations

import re
import statistics
import textwrap
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Final, NamedTuple

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from imgtests.types import MetricSample

if TYPE_CHECKING:
    from imgtests.database.database import ImgtestsDatabase
    from imgtests.database.models.experiment import ExperimentBase
    from imgtests.planning.executor import PlanExecutionResult
    from imgtests.planning.models import TestPlan


PLOTS_DIR: Final = "plots"
REPORT_FILENAME: Final = "report.html"

TEMPLATES_DIR: Final = "templates"
STATIC_DIR: Final = "static"
REPORT_TEMPLATE: Final = "base_report.html.j2"


class DiagramConfig(NamedTuple):
    run: str
    metrics: list[str]


DIAGRAMS_CONFIG: dict[str, DiagramConfig] = {
    "histogram_by_prefix": DiagramConfig(
        run="_build_histograms_by_prefix",
        metrics=[
            r"^systemd_critical_chain.",
            r"^systemd_time.",
        ],
    ),
    "boxplots": DiagramConfig(
        run="_build_boxplots",
        metrics=[
            r"stress.",
            r"fio.",
        ],
    ),
}
COMPILED_DIAGRAMS_CONFIG: dict[str, tuple[str, list[re.Pattern]]] = {
    name: (cfg.run, [re.compile(p) for p in cfg.metrics]) for name, cfg in DIAGRAMS_CONFIG.items()
}


@dataclass(frozen=True)
class StatsRow:
    stage_name: str
    subsystem: str
    metric_name: str
    count: int
    mean: float
    variance: float
    q25: float
    q50: float
    q75: float
    q95: float
    min_v: float
    max_v: float


@dataclass(frozen=True)
class StageTimelineRow:
    stage_name: str
    pattern: str
    planned_start_sec: int
    planned_duration_sec: int
    actual_started: str
    actual_ended: str
    actual_duration_sec: str
    tasks: int
    failures: int


@dataclass(frozen=True)
class PlotAsset:
    title: str
    relative_path: str


def generate_compare_html_report(
    experiments_id: list[int],
    database: ImgtestsDatabase,
    out_dir: Path,
):
    pass


def _extract_metrics_from_experiment(experiment: ExperimentBase) -> list[MetricSample]:
    metrics: list[MetricSample] = []

    for loader in experiment.loaders:
        if loader.description == "Planned stage":
            continue
        if loader.result and isinstance(loader.result, dict):
            metrics.extend(
                MetricSample(
                    stage_name=m.get("stage_name", ""),
                    subsystem=m.get("subsystem", "all"),
                    metric_name=m.get("metric_name", "unknown_tool"),
                    value=float(m.get("value", 0)),
                    label=m.get("label", "unknown_metric"),
                )
                for m in loader.result.get("metrics", [])
            )

    for observer in experiment.observers:
        if observer.description == "Planned stage":
            continue
        if observer.result and isinstance(observer.result, dict):
            metrics.extend(
                MetricSample(
                    stage_name=m.get("stage_name", ""),
                    subsystem=m.get("subsystem", "all"),
                    metric_name=m.get("metric_name", "unknown_tool"),
                    value=float(m.get("value", 0)),
                    label=m.get("label", "unknown_metric"),
                )
                for m in observer.result.get("metrics", [])
            )
    return metrics


def generate_html_report(plan: TestPlan, execution: PlanExecutionResult, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = out_dir / PLOTS_DIR
    plots_dir.mkdir(parents=True, exist_ok=True)

    metrics = list(execution.metrics)

    report_data = {
        "header": {
            "test_kind": plan.test_kind,
            "plan_id": plan.plan_id,
            "experiment_id": execution.experiment_id,
            "started_at": execution.started_at.isoformat(),
            "ended_at": execution.ended_at.isoformat(),
            "tests_counts": execution.tests_counts,
            "tests_stats": _build_piechart(
                {k: v for k, v in execution.tests_counts._asdict().items() if k != "total_count"},
                out_dir=out_dir,
                plots_dir=plots_dir,
                title="Test result statistics",
            ),
        },
        "timeline": {
            "overall_rows": _compute_stats(metrics, by_stage=False),
            "per_stage_rows": _compute_stats(metrics, by_stage=True),
            "timeline_rows": _build_timeline_rows(plan, execution),
        },
        "visualizations": _collect_test_visualizations(
            execution.metrics,
            out_dir=out_dir,
            plots_dir=plots_dir,
        ),
    }

    template = _template_environment().get_template(REPORT_TEMPLATE)
    report_path = out_dir / REPORT_FILENAME
    report_path.write_text(
        template.render(
            **report_data,
        ),
        encoding="utf-8",
    )
    return report_path


def _collect_test_visualizations(
    samples: list[MetricSample],
    out_dir: Path,
    plots_dir: Path,
) -> dict[str, list[PlotAsset]]:
    results: dict[str, list[PlotAsset]] = {}

    for name, (run_fn, patterns) in COMPILED_DIAGRAMS_CONFIG.items():
        matched = [s for s in samples if any(p.match(s.metric_name) for p in patterns)]
        if not matched and patterns:
            continue

        fn = globals()[run_fn]
        results[name] = fn(matched, out_dir=out_dir, plots_dir=plots_dir)

    return results


@lru_cache(maxsize=1)
def _template_environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(
            [
                Path(__file__).with_name(TEMPLATES_DIR),
                Path(__file__).with_name(STATIC_DIR),
            ],
        ),
        autoescape=select_autoescape(("html", "xml")),
        lstrip_blocks=True,
        trim_blocks=True,
        undefined=StrictUndefined,
    )
    env.filters["format_float"] = _format_float
    return env


def _build_timeline_rows(
    plan: TestPlan,
    execution: PlanExecutionResult,
) -> list[StageTimelineRow]:
    stage_run_map = {stage.stage_name: stage for stage in execution.stage_runs}
    rows: list[StageTimelineRow] = []

    for stage in plan.stages:
        run = stage_run_map.get(stage.name)
        failures = sum(1 for task in (run.tasks if run else ()) if task.returncode != 0)

        rows.append(
            StageTimelineRow(
                stage_name=stage.name,
                pattern=stage.pattern.value,
                planned_start_sec=stage.start_offset_sec,
                planned_duration_sec=stage.duration_sec,
                actual_started=run.started_at.isoformat() if run else "-",
                actual_ended=run.ended_at.isoformat() if run else "-",
                actual_duration_sec=(
                    f"{(run.ended_at - run.started_at).total_seconds():.2f}" if run else "-"
                ),
                tasks=len(stage.tasks),
                failures=failures,
            ),
        )

    return rows


def _compute_stats(samples: list[MetricSample], by_stage: bool) -> list[StatsRow]:
    grouped: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for sample in samples:
        stage_name = sample.stage_name if by_stage else "ALL"
        grouped[(stage_name, sample.subsystem, sample.metric_name)].append(float(sample.value))

    rows: list[StatsRow] = []
    for (stage_name, subsystem, metric_name), values in sorted(grouped.items()):
        values_sorted = sorted(values)
        if not values_sorted:
            continue

        count = len(values_sorted)
        variance = statistics.pvariance(values_sorted) if count > 1 else 0.0

        rows.append(
            StatsRow(
                stage_name=stage_name,
                subsystem=subsystem,
                metric_name=metric_name,
                count=count,
                mean=statistics.fmean(values_sorted),
                variance=variance,
                q25=_quantile(values_sorted, 0.25),
                q50=_quantile(values_sorted, 0.50),
                q75=_quantile(values_sorted, 0.75),
                q95=_quantile(values_sorted, 0.95),
                min_v=values_sorted[0],
                max_v=values_sorted[-1],
            ),
        )

    return rows


def _quantile(sorted_values: list[float], q: float) -> float:
    count = len(sorted_values)
    if count == 0:
        return 0.0
    if count == 1:
        return sorted_values[0]

    pos = (count - 1) * q
    lo = int(pos)
    hi = min(lo + 1, count - 1)
    frac = pos - lo
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * frac


def _build_boxplots(
    samples: list[MetricSample],
    *,
    out_dir: Path,
    plots_dir: Path,
) -> list[PlotAsset]:
    metric_to_subsystems: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for sample in samples:
        metric_to_subsystems[sample.metric_name][sample.subsystem].append(float(sample.value))

    plot_assets: list[PlotAsset] = []

    for metric_name in sorted(metric_to_subsystems):
        labels: list[str] = []
        values: list[list[float]] = []

        for subsystem in sorted(metric_to_subsystems[metric_name]):
            subsystem_values = metric_to_subsystems[metric_name][subsystem]
            if subsystem_values:
                labels.append(subsystem)
                values.append(subsystem_values)

        if not values:
            continue

        fig = Figure(figsize=(10, 4))
        FigureCanvasAgg(fig)
        ax = fig.add_subplot(1, 1, 1)
        ax.boxplot(values, labels=labels, showmeans=True)
        ax.set_title(metric_name)
        ax.set_xlabel("Subsystem")
        ax.set_ylabel("Value")
        ax.grid(visible=True, axis="y", alpha=0.3)

        out_path = plots_dir / f"{_safe_filename(metric_name)}.png"
        fig.tight_layout()
        fig.savefig(out_path)

        plot_assets.append(
            PlotAsset(
                title=metric_name,
                relative_path=str(out_path.relative_to(out_dir)),
            ),
        )

    return plot_assets


def _build_piechart(
    metrics: dict,
    title: str,
    *,
    out_dir: Path,
    plots_dir: Path,
) -> PlotAsset:
    fig = Figure(figsize=(8, 6))
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(1, 1, 1)
    values = list(metrics.values())
    wedges, _, _ = ax.pie(
        values,
        startangle=90,
        autopct=lambda pct: f"{round(pct / 100 * sum(values))}",
        textprops={"color": "white", "weight": "bold"},
    )
    ax.legend(
        wedges,
        list(metrics.keys()),
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1),
    )
    ax.set_title(title)
    out_path = plots_dir / f"{_safe_filename(title)}.png"
    fig.tight_layout()
    fig.savefig(out_path)
    return PlotAsset(
        title=title,
        relative_path=str(out_path.relative_to(out_dir)),
    )


def _build_histograms_by_prefix(
    metrics: list[MetricSample],
    *,
    out_dir: Path,
    plots_dir: Path,
) -> list[PlotAsset]:
    grouped = defaultdict(list)
    for m in metrics:
        if "." in m.metric_name:
            grouped[m.metric_name.split(".")[0]].append(m)

    assets = []
    for prefix, group in grouped.items():
        labels = [textwrap.fill(m.label, 15) for m in group]
        values = [m.value for m in group]

        fig = Figure(figsize=(8, 6))
        FigureCanvasAgg(fig)
        ax = fig.add_subplot(1, 1, 1)
        bars = ax.bar(range(len(labels)), values)
        ax.set_title(f"{prefix} metrics")
        ax.grid(visible=True, axis="y", alpha=0.3)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=60, ha="right")

        for bar, val in zip(bars, values, strict=True):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{val:.2f}",
                ha="center",
                va="bottom",
            )

        out_path = plots_dir / f"{_safe_filename(prefix)}.png"
        fig.tight_layout()
        fig.savefig(out_path)

        assets.append(
            PlotAsset(
                title=prefix,
                relative_path=str(out_path.relative_to(out_dir)),
            ),
        )
    return assets


def _format_float(value: float) -> str:
    return f"{value:.6g}"


def _safe_filename(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", name).strip("_")
    if not safe:
        return "metric"
    return safe
