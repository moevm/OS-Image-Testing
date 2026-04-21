from __future__ import annotations

import logging
import re
import statistics
import textwrap
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Final, NamedTuple
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from matplotlib import cm
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
COMPARE_REPORT_FILENAME: Final = "compare.html"

TEMPLATES_DIR: Final = "templates"
STATIC_DIR: Final = "static"
REPORT_TEMPLATE: Final = "base_report.html.j2"
COMPARE_REPORT_TEMPLATE: Final = "compare_report.html.j2"


class DiagramConfig(NamedTuple):
    run: str
    metrics: list[str]


DIAGRAMS_CONFIG: dict[str, DiagramConfig] = {
    "histogram_by_prefix": DiagramConfig(
        run="_build_histograms_by_prefix",
        metrics=[
            r"systemd_critical_chain.",
            r"systemd_time.",
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


class ReportGenerator:
    def __init__(self, database: ImgtestsDatabase):
        self._database = database
        self._logger = logging.getLogger()

    def generate_compare_html_report(
        self,
        experiments_id: list[int],
        out_dir: Path,
    ) -> Path | None:
        if len(experiments_id) < 2:  #  noqa: PLR2004
            self._logger.error(
                "Couldn't build a report: there are less than two experiments in the database.",
            )
            return None
        compare_dir = out_dir / f"compare-{experiments_id[0]}-{experiments_id[1]}"
        compare_dir.mkdir(parents=True, exist_ok=True)
        plots_dir = compare_dir / PLOTS_DIR
        plots_dir.mkdir(parents=True, exist_ok=True)
        report_data = []
        exps_data = []

        metrics_by_exp: list[list[MetricSample]] = []
        for exp_id in experiments_id:
            exp_data = self._database.get_experiment_with_details(exp_id)
            exps_data.append(exp_data)
            metrics_by_exp.append(self._extract_metrics_from_experiment(exp_data))

        unique_metrics_by_exp, common_metrics = self.__distribute_metrics(
            metrics_by_exp,
            experiments_id,
        )

        for i in range(len(exps_data)):
            exp_data = exps_data[i]
            metrics = self._extract_metrics_from_experiment(exp_data)
            report_data.append(
                {
                    "header": {
                        "test_kind": exp_data.description,
                        "configuration": exp_data.configuration,
                        "experiment_id": exp_data.experiment_id,
                        "started_at": exp_data.started_at.isoformat(),
                        "ended_at": exp_data.ended_at.isoformat(),
                        "tests_counts": {
                            "skip_count": exp_data.tests_skipped,
                            "broken_count": exp_data.tests_broken,
                            "failed_count": exp_data.tests_failed,
                            "passed_count": exp_data.tests_passed,
                            "total_count": exp_data.tests_total,
                        },
                        "tests_stats": _build_piechart(
                            {
                                "skip_count": exp_data.tests_skipped,
                                "broken_count": exp_data.tests_broken,
                                "passed_count": exp_data.tests_passed,
                                "failed_count": exp_data.tests_failed,
                            },
                            out_dir=compare_dir,
                            plots_dir=plots_dir,
                            title="Test result statistics",
                        ),
                    },
                    "timeline": {
                        "overall_rows": _compute_stats(metrics, by_stage=False),
                        "per_stage_rows": _compute_stats(metrics, by_stage=True),
                    },
                    "unique_visualizations": self.collect_test_visualizations(
                        unique_metrics_by_exp[i],
                        out_dir=compare_dir,
                        plots_dir=plots_dir,
                    ),
                },
            )
        template = _template_environment().get_template(COMPARE_REPORT_TEMPLATE)
        report_path = compare_dir / COMPARE_REPORT_FILENAME
        report_path.write_text(
            template.render(
                exps_data=report_data,
                common_visualizations=self.collect_test_visualizations(
                    common_metrics,
                    out_dir=compare_dir,
                    plots_dir=plots_dir,
                ),
            ),
            encoding="utf-8",
        )
        return report_path

    def generate_last_two_experiments_report(self, out_dir: Path) -> Path | None:
        ids = self._database.get_last_two_experiment_ids()
        if len(ids) < 2:  #  noqa: PLR2004
            self._logger.error(
                "Couldn't build a report: there are less than two experiments in the database.",
            )
            return None
        return self.generate_compare_html_report(sorted(ids), out_dir)

    def __distribute_metrics(
        self,
        metrics_by_exp: list[list[MetricSample]],
        experiments_id: list[int],
    ) -> tuple[list[list[MetricSample]], list[MetricSample]]:
        unique_metrics_by_exp: list[list[MetricSample]] = []
        common_metrics: list[MetricSample] = []

        prefix_sets = []
        for metrics in metrics_by_exp:
            prefixes = {m.metric_name.split(".")[0] for m in metrics if "." in m.metric_name}
            prefix_sets.append(prefixes)

        common_prefixes = set.intersection(*prefix_sets) if prefix_sets else set()

        for exp_idx, exp_metrics in enumerate(metrics_by_exp):
            exp_id = experiments_id[exp_idx]
            unique_for_exp: list[MetricSample] = []

            for m in exp_metrics:
                prefix = m.metric_name.split(".")[0] if "." in m.metric_name else m.metric_name
                if prefix not in common_prefixes:
                    unique_for_exp.append(m)
                else:
                    common_metrics.append(
                        MetricSample(
                            stage_name=m.stage_name,
                            subsystem=m.subsystem,
                            metric_name=f"exp_{exp_id}.{m.metric_name}",
                            value=m.value,
                            label=m.label,
                        ),
                    )
            unique_metrics_by_exp.append(unique_for_exp)

        return unique_metrics_by_exp, common_metrics

    def _extract_metrics_from_experiment(self, experiment: ExperimentBase) -> list[MetricSample]:
        metrics: list[MetricSample] = []

        for util_run_result in experiment.util_run_results:
            if util_run_result.description == "Planned stage":
                continue
            if util_run_result.result and isinstance(util_run_result.result, dict):
                metrics.extend(
                    MetricSample(
                        stage_name=m.get("stage_name", ""),
                        subsystem=m.get("subsystem", "all"),
                        metric_name=m.get("metric_name", "unknown_tool"),
                        value=float(m.get("value", 0)),
                        label=m.get("label", "unknown_metric"),
                    )
                    for m in util_run_result.result.get("metrics", [])
                )
        return metrics

    @staticmethod
    def generate_profiled_html_report(
        plan: TestPlan,
        execution: PlanExecutionResult,
        out_dir: Path,
    ) -> Path:
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
                    {
                        "skip_count": execution.tests_counts.skip_count,
                        "broken_count": execution.tests_counts.broken_count,
                        "passed_count": execution.tests_counts.passed_count,
                        "failed_count": execution.tests_counts.failed_count,
                    },
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
            "visualizations": ReportGenerator.collect_test_visualizations(
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

    @staticmethod
    def collect_test_visualizations(
        samples: list[MetricSample],
        out_dir: Path,
        plots_dir: Path,
    ) -> dict[str, list[PlotAsset]]:
        results: dict[str, list[PlotAsset]] = {}

        for name, (run_fn, patterns) in COMPILED_DIAGRAMS_CONFIG.items():
            matched = []
            for s in samples:
                normalized_name = re.sub(r"^exp_\d+\.", "", s.metric_name)
                if any(p.match(normalized_name) for p in patterns):
                    matched.append(s)
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
    metric_to_subsystems: dict[str, dict[str, dict[str, list[float]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list)),
    )
    for sample in samples:
        parts = sample.metric_name.split(".")
        if parts[0].startswith("exp_"):
            exp_prefix = parts[0]
            metric_core = ".".join(parts[1:])
        else:
            exp_prefix = "common"
            metric_core = sample.metric_name

        metric_to_subsystems[metric_core][sample.subsystem][exp_prefix].append(float(sample.value))

    plot_assets: list[PlotAsset] = []

    for metric_name in sorted(metric_to_subsystems):
        labels: list[str] = []
        values: list[list[float]] = []

        for subsystem in sorted(metric_to_subsystems[metric_core]):
            exp_groups = metric_to_subsystems[metric_core][subsystem]
            for exp_prefix, vals in exp_groups.items():
                if vals:
                    label = subsystem if exp_prefix == "common" else f"{subsystem} ({exp_prefix})"
                    labels.append(textwrap.fill(label, 15))
                    values.append(vals)

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

        for tick in ax.get_xticklabels():
            tick.set_rotation(60)
            tick.set_ha("right")

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
    grouped = defaultdict(lambda: defaultdict(list))
    for m in metrics:
        parts = m.metric_name.split(".")
        if parts[0].startswith("exp_"):
            exp_prefix = parts[0]
            util_prefix = parts[1]
            metric_core = ".".join(parts[2:]) if len(parts) > 2 else parts[1]  #  noqa: PLR2004
        else:
            exp_prefix = "common"
            util_prefix = parts[0]
            metric_core = ".".join(parts[1:]) if len(parts) > 1 else parts[0]

        grouped[util_prefix][exp_prefix].append((metric_core, m))

    assets = []
    for util_prefix, exp_groups in grouped.items():
        fig = Figure(figsize=(10, 6))
        FigureCanvasAgg(fig)
        ax = fig.add_subplot(1, 1, 1)

        all_metric_names = []
        for group in exp_groups.values():
            for metric_core, _ in group:
                if metric_core not in all_metric_names:
                    all_metric_names.append(metric_core)

        exp_labels = list(exp_groups.keys())
        cmap = cm.get_cmap("tab10", len(exp_labels))
        values_by_exp = []
        for exp_prefix in exp_labels:
            label_to_value = {core: m.value for core, m in exp_groups[exp_prefix]}
            values = [label_to_value.get(core, 0.0) for core in all_metric_names]
            values_by_exp.append(values)

        x = range(len(all_metric_names))
        width = 0.8 / len(exp_labels)

        for i, values in enumerate(values_by_exp):
            ax.bar(
                [pos + i * width for pos in x],
                values,
                width=width,
                label=exp_labels[i],
                color=cmap(i),
            )
        ax.set_title(f"{util_prefix} metrics")
        ax.set_xticks([pos + width * (len(exp_labels) - 1) / 2 for pos in x])
        ax.set_xticklabels(all_metric_names, rotation=60, ha="right")
        ax.legend(title="Experiments")
        ax.grid(visible=True, axis="y", alpha=0.3)
        out_path = plots_dir / f"{_safe_filename(util_prefix)}.png"
        fig.tight_layout()
        fig.savefig(out_path)

        assets.append(
            PlotAsset(
                title=util_prefix,
                relative_path=str(out_path.relative_to(out_dir)),
            ),
        )
    return assets


def _format_float(value: float) -> str:
    return f"{value:.6g}"


def _safe_filename(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", name).strip("_")
    if not safe:
        return f"metric_{datetime.now(tz=ZoneInfo('UTC')).strftime('%Y%m%d_%H%M%S')}"
    return f"{safe}_{datetime.now(tz=ZoneInfo('UTC')).strftime('%Y%m%d_%H%M%S_%f')}"
