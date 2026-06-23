from __future__ import annotations

import json
import logging
import re
import statistics
import textwrap
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, NamedTuple

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from matplotlib import cm
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure
from pydantic import Field
from pydantic_settings import BaseSettings

from imgtests.constant import LIB_NAME
from imgtests.exec.exec import common_run_command
from imgtests.types import MetricSample, Subsystem

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

SYSTEM_ERROR_DESCRIPTIONS: Final = {
    "failed systemd services",
    "OOM records",
    "systemd errors records",
}

YOCTO_JOB: Final = "yocto-node"
SUSE_JOB: Final = "suse-156-node"

BOXPLOT_DISTRIBUTION_COLORS: Final = {
    "poky": "#2E7D32",
    "yocto": "#2E7D32",
    "opensuse": "#1565C0",
    "suse": "#1565C0",
}
BOXPLOT_COMMON_COLOR: Final = "#4D4D4D"
BOXPLOT_FACE_ALPHA: Final = 0.18


class VMetricsCreds(BaseSettings):
    host: str = Field(validation_alias="VMETRICS_ADDRESS")
    port: int = Field(validation_alias="VMETRICS_PORT")


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
            r"stress-ng.",
            r"fio.",
            r"iperf3.",
            r"kirk.",
            r"pts.",
            r"perf.",
        ],
    ),
}
COMPILED_DIAGRAMS_CONFIG: dict[str, tuple[str, list[re.Pattern]]] = {
    name: (cfg.run, [re.compile(p) for p in cfg.metrics]) for name, cfg in DIAGRAMS_CONFIG.items()
}

TOOLS_TO_SUBSYSTEMS: dict[str, Subsystem] = {
    "iperf3": Subsystem.NETWORK,
    "fio": Subsystem.FILE,
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
        self._logger = logging.getLogger(f"{LIB_NAME}.report_generator")

    def generate_compare_html_report(
        self,
        experiment_ids: list[int],
        out_dir: Path,
    ) -> Path | None:
        if len(experiment_ids) != 2:  #  noqa: PLR2004
            self._logger.error(
                "Couldn't build a report: there are incorrect amount of experiments.",
            )
            return None
        compare_dir = out_dir / f"compare-{experiment_ids[0]}-{experiment_ids[1]}"
        compare_dir.mkdir(parents=True, exist_ok=True)
        plots_dir = compare_dir / PLOTS_DIR
        plots_dir.mkdir(parents=True, exist_ok=True)
        report_data = []
        exps_data = []

        metrics_by_exp: list[list[MetricSample]] = []
        exps_os = []
        for exp_id in experiment_ids:
            exp_data = self._database.get_experiment_with_details(exp_id)
            exps_os.append(exp_data.configuration.os.split()[0])
            exps_data.append(exp_data)
            metrics_by_exp.append(self._extract_metrics_from_experiment(exp_data))

        unique_metrics_by_exp, common_metrics = self.__distribute_metrics(
            metrics_by_exp,
            exps_os,
        )

        for i in range(len(exps_data)):
            exp_data = exps_data[i]
            metrics = self._extract_metrics_from_experiment(exp_data)
            job_name = (
                YOCTO_JOB
                if "poky" in exp_data.configuration.os.lower()
                or "yocto" in exp_data.configuration.os.lower()
                else SUSE_JOB
            )
            self.add_load_average_metrics(metrics, exp_data.started_at, exp_data.ended_at, job_name)
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

    def __distribute_metrics(
        self,
        metrics_by_exp: list[list[MetricSample]],
        experiments_os: list[str],
    ) -> tuple[list[list[MetricSample]], list[MetricSample]]:
        unique_metrics_by_exp: list[list[MetricSample]] = []
        common_metrics: list[MetricSample] = []

        prefix_sets = []
        for metrics in metrics_by_exp:
            prefixes = {m.metric_name.split(".")[0] for m in metrics if "." in m.metric_name}
            prefix_sets.append(prefixes)

        common_prefixes = set.intersection(*prefix_sets) if prefix_sets else set()

        for exp_idx, exp_metrics in enumerate(metrics_by_exp):
            exp_os = experiments_os[exp_idx]
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
                            metric_name=f"{exp_os.replace(' ', '_')}${m.metric_name}",
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
            result = util_run_result.result

            if util_run_result.description in SYSTEM_ERROR_DESCRIPTIONS:
                value = float(len(result)) if isinstance(result, list) else float(result)
                metrics.append(
                    MetricSample(
                        stage_name="system-errors",
                        subsystem="system",
                        metric_name=util_run_result.description,
                        value=value,
                        label=util_run_result.description,
                    ),
                )
                continue

            if not result or not isinstance(result, dict) or "metrics" not in result:
                continue
            if isinstance(result.get("metrics"), list):
                metrics.extend(
                    MetricSample(
                        stage_name=m.get("stage_name", ""),
                        subsystem=m.get("subsystem", "unknown"),
                        metric_name=m.get("metric_name", "unknown_tool"),
                        value=float(m.get("value", 0)),
                        label=m.get("label", "unknown_metric"),
                    )
                    for m in util_run_result.result.get("metrics", [])
                    if isinstance(m, dict)
                )
            if isinstance(result.get("metrics"), dict) and all(
                k in result for k in ("tool", "test_type", "metrics")
            ):
                tool = result.get("tool")
                test_type = result.get("test_type")
                stage_name = (
                    " ".join(f"{k}:{v}" for k, v in test_type.items() if not isinstance(v, dict))
                    or "tool_stage"
                )
                subsystem = TOOLS_TO_SUBSYSTEMS.get(tool)
                if subsystem is None:
                    subsystem = test_type.get("stressor", "unknown")
                match tool:
                    case "iperf3":
                        fixed_prefix = [tool, test_type["protocol"]]
                    case "pts":
                        fixed_prefix = [tool, test_type["identifier"]]
                    case "perf":
                        fixed_prefix = [tool, test_type["benchmark"]]
                    case _:
                        fixed_prefix = [tool]

                metrics.extend(
                    self._walk_metrics(
                        d=result["metrics"],
                        tool=tool,
                        stage_name=stage_name,
                        fixed_prefix=fixed_prefix,
                        prefix=[],
                        subsystem=subsystem,
                    ),
                )
        return metrics

    def _walk_metrics(  #  noqa: PLR0913
        self,
        d: dict,
        tool: str,
        stage_name: str,
        fixed_prefix: list[str],
        prefix: list[str],
        subsystem: str = "unknown",
    ) -> list[MetricSample]:
        collected: list[MetricSample] = []
        if "stressor" in d:
            if subsystem == "unknown":
                subsystem = d.get("stressor", subsystem)
            else:
                subsystem = f"{subsystem}_{d.get('stressor')}"
        if tool == "kirk" and "test" in d:
            fixed_prefix = [tool, d["test"]]

        for k, v in d.items():
            if k == "summary":
                continue
            if k.isdigit() and isinstance(v, dict):
                collected.extend(
                    self._walk_metrics(v, tool, stage_name, fixed_prefix, prefix, subsystem),
                )
            elif isinstance(v, dict):
                collected.extend(
                    self._walk_metrics(v, tool, stage_name, fixed_prefix, [*prefix, k], subsystem),
                )
            elif isinstance(v, (int, float)):
                metric_name = ".".join(fixed_prefix + prefix + [k])
                label = ".".join(fixed_prefix + [*prefix, k][-2:])
                collected.append(
                    MetricSample(
                        stage_name=stage_name,
                        subsystem=subsystem,
                        metric_name=metric_name,
                        value=float(v),
                        label=label,
                    ),
                )
            elif isinstance(v, list):
                if not all(isinstance(x, (int, float)) for x in v):
                    continue
                metric_name = ".".join(fixed_prefix + prefix + [k])
                label = ".".join(fixed_prefix + [*prefix, k][-2:])
                collected.extend(
                    MetricSample(
                        stage_name=stage_name,
                        subsystem=subsystem,
                        metric_name=metric_name,
                        value=float(val),
                        label=label,
                    )
                    for val in v
                )
        return collected

    @staticmethod
    def generate_profiled_html_report(
        plan: TestPlan,
        execution: PlanExecutionResult,
        out_dir: Path,
        job_name: str | None,
    ) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        plots_dir = out_dir / PLOTS_DIR
        plots_dir.mkdir(parents=True, exist_ok=True)

        metrics = list(execution.metrics)
        ReportGenerator.add_load_average_metrics(
            metrics,
            execution.started_at,
            execution.ended_at,
            job_name,
        )

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
                normalized_name = re.sub(r"^[^$]+\$", "", s.metric_name)
                if any(p.match(normalized_name) for p in patterns):
                    matched.append(s)
            if not matched and patterns:
                continue

            fn = globals()[run_fn]
            results[name] = fn(matched, out_dir=out_dir, plots_dir=plots_dir)

        return results

    @staticmethod
    def add_load_average_metrics(
        metrics: list[MetricSample],
        start_time: datetime,
        end_time: datetime,
        job_name: str | None,
    ) -> None:
        vmetrics_creds = VMetricsCreds()
        start_time = start_time.astimezone(UTC).isoformat().replace("+00:00", "Z")
        end_time = end_time.astimezone(UTC).isoformat().replace("+00:00", "Z")
        for interval in (1, 5, 15):
            if not job_name:
                query_url = (
                    f"http://{vmetrics_creds.host}:{vmetrics_creds.port}/api/v1/query_range"
                    f"?query=node_load{interval}&start={start_time}&end={end_time}&step=1m"
                )
            else:
                query_url = (
                    f"http://{vmetrics_creds.host}:{vmetrics_creds.port}/api/v1/query_range"
                    f'?query=node_load{interval}{{job="{job_name}"}}'
                    f"&start={start_time}&end={end_time}&step=1m"
                )
            result = common_run_command(["curl", "--globoff", query_url])
            if result.returncode:
                return

            query_result = json.loads(result.stdout).get("data", {}).get("result", [])
            if query_result == []:
                return

            for _, value in query_result[0].get("values", []):
                metrics.append(
                    MetricSample(
                        stage_name="load_average",
                        subsystem="cpu",
                        metric_name=f"load_average_{interval}min",
                        value=float(value),
                        label=f"load_average_{interval}min",
                    ),
                )


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
        parts = sample.metric_name.split("$")
        if len(parts) > 1:
            exp_prefix = parts[0].replace("_", " ")
            metric_core = ".".join(parts[1:])
        else:
            exp_prefix = "common"
            metric_core = sample.metric_name

        metric_to_subsystems[metric_core][sample.subsystem][exp_prefix].append(float(sample.value))
    plot_assets: list[PlotAsset] = []

    for metric_name in sorted(metric_to_subsystems):
        labels: list[str] = []
        values: list[list[float]] = []
        distros: list[str] = []

        for subsystem in sorted(metric_to_subsystems[metric_name]):
            exp_groups = metric_to_subsystems[metric_name][subsystem]
            for exp_prefix, vals in exp_groups.items():
                if vals:
                    label = subsystem if exp_prefix == "common" else f"{subsystem} ({exp_prefix})"
                    labels.append(textwrap.fill(label, 15))
                    values.append(vals)
                    distros.append(exp_prefix)

        if not values:
            continue

        fig = Figure(figsize=(10, 4))
        FigureCanvasAgg(fig)
        ax = fig.add_subplot(1, 1, 1)
        boxplot = ax.boxplot(values, labels=labels, showmeans=True, patch_artist=True)
        _style_boxplot_by_distro(boxplot, distros)
        ax.set_title(metric_name)
        ax.set_xlabel("Subsystem")
        ax.set_ylabel("Value")
        ax.grid(visible=True, axis="y", alpha=0.3)

        for tick in ax.get_xticklabels():
            tick.set_rotation(30)
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


def _style_boxplot_by_distro(boxplot: dict[str, list[Any]], distros: list[str]) -> None:
    colors = [_boxplot_color(distro) for distro in distros]

    for box, color in zip(boxplot["boxes"], colors, strict=True):
        box.set_facecolor(to_rgba(color, BOXPLOT_FACE_ALPHA))
        box.set_edgecolor(color)
        box.set_linewidth(1.4)

    for median, color in zip(boxplot["medians"], colors, strict=True):
        median.set_color(color)
        median.set_linewidth(1.4)

    for mean, color in zip(boxplot["means"], colors, strict=True):
        mean.set_markerfacecolor(color)
        mean.set_markeredgecolor(color)

    for line_type in ("whiskers", "caps"):
        for index, line in enumerate(boxplot[line_type]):
            color = colors[index // 2]
            line.set_color(color)
            line.set_linewidth(1.2)

    for flier, color in zip(boxplot["fliers"], colors, strict=True):
        flier.set_markeredgecolor(color)
        flier.set_alpha(0.6)


def _boxplot_color(distro: str) -> str:
    normalized = _normalize_distro_name(distro)
    if normalized == "common":
        return BOXPLOT_COMMON_COLOR
    for known_distro, color in BOXPLOT_DISTRIBUTION_COLORS.items():
        if known_distro in normalized:
            return color
    msg = f"Unknown distribution for boxplot color: {distro}"
    raise ValueError(msg)


def _normalize_distro_name(distro: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", distro.casefold()).strip("-")


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
        parts = m.metric_name.split("$", 1)
        if len(parts) > 1:
            exp_prefix = parts[0].replace("_", " ")
            subparts = parts[1].split(".")
        else:
            exp_prefix = "common"
            subparts = parts[0].split(".")
        util_prefix = subparts[0]
        metric_core = ".".join(subparts[1:]) if len(subparts) > 1 else util_prefix

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
        ax.set_xticklabels(all_metric_names, rotation=30, ha="right")
        if len(exp_labels) > 1:
            ax.legend(title="OS")
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
        return f"metric_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
    return f"{safe}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S_%f')}"
