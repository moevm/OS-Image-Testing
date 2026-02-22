from __future__ import annotations

import html
import re
import statistics
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt

if TYPE_CHECKING:
    from pathlib import Path

    from imgtests.planning.executor import MetricSample, PlanExecutionResult
    from imgtests.planning.models import TestPlan


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


def generate_html_report(plan: TestPlan, execution: PlanExecutionResult, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = out_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    overall_rows = _compute_stats(list(execution.metrics), by_stage=False)
    per_stage_rows = _compute_stats(list(execution.metrics), by_stage=True)
    plot_files = _build_boxplots(list(execution.metrics), plots_dir)

    stage_run_map = {x.stage_name: x for x in execution.stage_runs}
    total_tasks = sum(len(x.tasks) for x in execution.stage_runs)
    failed_tasks = sum(1 for s in execution.stage_runs for t in s.tasks if t.returncode != 0)

    html_lines: list[str] = []
    html_lines.append("<!doctype html>")
    html_lines.append("<html lang='en'>")
    html_lines.append("<head>")
    html_lines.append("<meta charset='utf-8'>")
    html_lines.append("<title>Load Test Report</title>")
    html_lines.append(
        "<style>"
        "body{font-family:Arial,Helvetica,sans-serif;margin:24px;line-height:1.45}"
        "h1,h2,h3{margin:0.2em 0}"
        "table{border-collapse:collapse;width:100%;margin:12px 0 24px 0}"
        "th,td{border:1px solid #ddd;padding:8px;font-size:14px}"
        "th{background:#f7f7f7;text-align:left}"
        ".ok{color:#116611;font-weight:700}"
        ".bad{color:#aa0000;font-weight:700}"
        ".muted{color:#666}"
        "img{max-width:100%;height:auto;border:1px solid #ddd;padding:6px;margin:8px 0 18px 0}"
        "code{background:#f2f2f2;padding:2px 4px;border-radius:3px}"
        "</style>"
    )
    html_lines.append("</head><body>")

    html_lines.append("<h1>Load/Stress Test Report</h1>")
    html_lines.append(
        f"<p class='muted'>Experiment ID: <b>{execution.experiment_id}</b> | "
        f"Plan ID: <b>{html.escape(plan.plan_id)}</b></p>"
    )
    html_lines.append(
        f"<p class='muted'>Started: {execution.started_at.isoformat()} | "
        f"Ended: {execution.ended_at.isoformat()}</p>"
    )
    html_lines.append(
        f"<p>Total tasks: <b>{total_tasks}</b> | "
        f"Failed: <b class='{'bad' if failed_tasks else 'ok'}'>{failed_tasks}</b></p>"
    )
    html_lines.append(f"<p>Plan file: <code>{html.escape(str(execution.plan_path))}</code></p>")

    html_lines.append("<h2>1) Plan Timeline</h2>")
    html_lines.append("<table>")
    html_lines.append(
        "<tr>"
        "<th>Stage</th><th>Pattern</th><th>Planned start, sec</th><th>Planned duration, sec</th>"
        "<th>Actual started</th><th>Actual ended</th><th>Actual duration, sec</th>"
        "<th>Tasks</th><th>Failures</th>"
        "</tr>"
    )
    for stage in plan.stages:
        run = stage_run_map.get(stage.name)
        actual_started = run.started_at.isoformat() if run else "-"
        actual_ended = run.ended_at.isoformat() if run else "-"
        actual_duration = f"{(run.ended_at - run.started_at).total_seconds():.2f}" if run else "-"
        failures = sum(1 for t in (run.tasks if run else []) if t.returncode != 0)
        html_lines.append(
            "<tr>"
            f"<td>{html.escape(stage.name)}</td>"
            f"<td>{html.escape(stage.pattern.value)}</td>"
            f"<td>{stage.start_offset_sec}</td>"
            f"<td>{stage.duration_sec}</td>"
            f"<td>{html.escape(actual_started)}</td>"
            f"<td>{html.escape(actual_ended)}</td>"
            f"<td>{actual_duration}</td>"
            f"<td>{len(stage.tasks)}</td>"
            f"<td>{failures}</td>"
            "</tr>"
        )
    html_lines.append("</table>")

    html_lines.append("<h2>2) Aggregated Statistics (Overall)</h2>")
    html_lines.append(
        "<p class='muted'>"
        "Mean, variance, quartiles and 95th percentile for collected numeric metrics "
        "(all stages merged)."
        "</p>"
    )
    html_lines.append(_render_stats_table(overall_rows, include_stage=False))

    html_lines.append("<h2>3) Statistics by Stage</h2>")
    html_lines.append("<p class='muted'>Same stats, but computed separately for each stage.</p>")
    html_lines.append(_render_stats_table(per_stage_rows, include_stage=True))

    html_lines.append("<h2>4) Boxplot Visualizations</h2>")
    if not plot_files:
        html_lines.append("<p>No plots were generated (not enough numeric samples).</p>")
    else:
        for plot in plot_files:
            rel = plot.relative_to(out_dir)
            html_lines.append(f"<h3>{html.escape(plot.stem)}</h3>")
            html_lines.append(f"<img src='{html.escape(str(rel))}' alt='{html.escape(plot.stem)}'>")

    html_lines.append("</body></html>")

    report_path = out_dir / "report.html"
    report_path.write_text("\n".join(html_lines), encoding="utf-8")
    return report_path


def _render_stats_table(rows: list[StatsRow], include_stage: bool) -> str:
    lines: list[str] = []
    lines.append("<table>")
    if include_stage:
        lines.append(
            "<tr>"
            "<th>Stage</th><th>Subsystem</th><th>Metric</th><th>N</th><th>Mean</th><th>Variance</th>"
            "<th>Q25</th><th>Q50</th><th>Q75</th><th>Q95</th><th>Min</th><th>Max</th>"
            "</tr>"
        )
    else:
        lines.append(
            "<tr>"
            "<th>Subsystem</th><th>Metric</th><th>N</th><th>Mean</th><th>Variance</th>"
            "<th>Q25</th><th>Q50</th><th>Q75</th><th>Q95</th><th>Min</th><th>Max</th>"
            "</tr>"
        )

    for row in rows:
        if include_stage:
            lines.append(
                "<tr>"
                f"<td>{html.escape(row.stage_name)}</td>"
                f"<td>{html.escape(row.subsystem)}</td>"
                f"<td>{html.escape(row.metric_name)}</td>"
                f"<td>{row.count}</td>"
                f"<td>{row.mean:.6g}</td>"
                f"<td>{row.variance:.6g}</td>"
                f"<td>{row.q25:.6g}</td>"
                f"<td>{row.q50:.6g}</td>"
                f"<td>{row.q75:.6g}</td>"
                f"<td>{row.q95:.6g}</td>"
                f"<td>{row.min_v:.6g}</td>"
                f"<td>{row.max_v:.6g}</td>"
                "</tr>"
            )
        else:
            lines.append(
                "<tr>"
                f"<td>{html.escape(row.subsystem)}</td>"
                f"<td>{html.escape(row.metric_name)}</td>"
                f"<td>{row.count}</td>"
                f"<td>{row.mean:.6g}</td>"
                f"<td>{row.variance:.6g}</td>"
                f"<td>{row.q25:.6g}</td>"
                f"<td>{row.q50:.6g}</td>"
                f"<td>{row.q75:.6g}</td>"
                f"<td>{row.q95:.6g}</td>"
                f"<td>{row.min_v:.6g}</td>"
                f"<td>{row.max_v:.6g}</td>"
                "</tr>"
            )
    lines.append("</table>")
    return "\n".join(lines)


def _compute_stats(samples: list[MetricSample], by_stage: bool) -> list[StatsRow]:
    grouped: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for sample in samples:
        stage = sample.stage_name if by_stage else "ALL"
        grouped[(stage, sample.subsystem, sample.metric_name)].append(float(sample.value))

    rows: list[StatsRow] = []
    for (stage, subsystem, metric), values in sorted(grouped.items()):
        values_sorted = sorted(values)
        cnt = len(values_sorted)
        if cnt == 0:
            continue

        mean_val = statistics.fmean(values_sorted)
        variance_val = statistics.pvariance(values_sorted) if cnt > 1 else 0.0

        rows.append(
            StatsRow(
                stage_name=stage,
                subsystem=subsystem,
                metric_name=metric,
                count=cnt,
                mean=mean_val,
                variance=variance_val,
                q25=_quantile(values_sorted, 0.25),
                q50=_quantile(values_sorted, 0.50),
                q75=_quantile(values_sorted, 0.75),
                q95=_quantile(values_sorted, 0.95),
                min_v=values_sorted[0],
                max_v=values_sorted[-1],
            )
        )
    return rows


def _quantile(sorted_values: list[float], q: float) -> float:
    n = len(sorted_values)
    if n == 0:
        return 0.0
    if n == 1:
        return sorted_values[0]

    pos = (n - 1) * q
    lo = int(pos)
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * frac


def _build_boxplots(samples: list[MetricSample], plots_dir: Path) -> list[Path]:
    metric_to_subsys: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for sample in samples:
        metric_to_subsys[sample.metric_name][sample.subsystem].append(float(sample.value))

    out_paths: list[Path] = []

    for metric_name in sorted(metric_to_subsys):
        by_sub = metric_to_subsys[metric_name]
        labels: list[str] = []
        values: list[list[float]] = []

        for subsystem in sorted(by_sub):
            vals = by_sub[subsystem]
            if vals:
                labels.append(subsystem)
                values.append(vals)

        if not values:
            continue

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.boxplot(values, labels=labels, showmeans=True)
        ax.set_title(metric_name)
        ax.set_xlabel("Subsystem")
        ax.set_ylabel("Value")
        ax.grid(visible=True, axis="y", alpha=0.3)

        out_path = plots_dir / f"{_safe_filename(metric_name)}.png"
        fig.tight_layout()
        fig.savefig(out_path)
        plt.close(fig)

        out_paths.append(out_path)

    return out_paths


def _safe_filename(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", name).strip("_")
    if not safe:
        return "metric"
    return safe
