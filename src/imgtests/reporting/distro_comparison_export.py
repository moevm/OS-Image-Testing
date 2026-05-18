from __future__ import annotations

import argparse
import logging
import math
import re
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from openpyxl import Workbook, load_workbook
from openpyxl.chart import AreaChart, BarChart, LineChart, Reference, StockChart
from openpyxl.chart.axis import ChartLines
from openpyxl.chart.updown_bars import UpDownBars
from openpyxl.styles import Font, PatternFill

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

logger = logging.getLogger(__name__)

DISTROS: Final = ("poky", "suse")
CONFIGURATION_SHEET: Final = "configuration"
EXPERIMENT_SHEET: Final = "experiment"
COMPARISON_OUTPUT_NAME: Final = "comparison"

COMPARISON_SELECTION_SHEET: Final = "comparison_selection"
COMPARISON_INDEX_SHEET: Final = "comparison_index"
COMPARISON_DATA_SHEET: Final = "comparison_data"
COMPARISON_CHARTS_PREFIX: Final = "comparison_charts"
CHART_SHEET_PREFIX: Final = "charts"

NONZERO_EPSILON: Final = 1e-12
INVALID_NUMERIC_SENTINELS: Final = {-1.0}
DEFAULT_MAX_CHARTS: Final = 0
DEFAULT_CHARTS_PER_SHEET: Final = 30
SHORT_TOKEN_LENGTH: Final = 3
EXPLICIT_PAIR_EXPERIMENT_COUNT: Final = 2
MIN_TREND_POINTS: Final = 3

SKIP_SOURCE_SHEETS: Final = {
    COMPARISON_SELECTION_SHEET,
    COMPARISON_INDEX_SHEET,
    COMPARISON_DATA_SHEET,
    COMPARISON_CHARTS_PREFIX,
    "comparison_metrics",
    "comparison_summary",
}

LABEL_COLUMNS: Final = {
    "distribution_id",
    "configuration_id",
    "distribution_description",
    "experiment_id",
    "run_result_id",
    "id",
    "test_name",
    "tool_name",
    "util_type",
    "command",
    "description",
    "started_at",
    "ended_at",
    "type",
    "config_id",
    "tests_total",
    "tests_passed",
    "tests_failed",
    "tests_broken",
    "tests_skipped",
}

TECHNICAL_TOKENS: Final = {
    "id",
    "pid",
    "uid",
    "gid",
    "fd",
    "rc",
    "code",
    "exit",
    "status",
    "returncode",
    "return",
    "retval",
    "ret",
    "socket",
    "port",
    "host",
    "hostname",
    "ip",
    "addr",
    "address",
    "local",
    "remote",
    "timestamp",
    "epoch",
    "unix",
    "version",
    "command",
    "cmd",
    "cookie",
    "mss",
    "tos",
}

TIME_PATTERNS: Final = {
    "systemd",
    "systemd_analyze",
    "duration",
    "elapsed",
    "runtime",
    "seconds",
    "secs",
    "time",
    "latency",
    "lat",
    "clat",
    "slat",
    "rtt",
    "wait",
}

THROUGHPUT_PATTERNS: Final = {
    "bps",
    "bits_per_second",
    "bitrate",
    "bandwidth",
    "bw",
    "iops",
    "ops_per_sec",
    "ops_s",
    "bogo_ops_s",
    "pps",
    "requests_per_second",
}

PERCENT_PATTERNS: Final = {
    "percent",
    "percentage",
    "pct",
    "ratio",
    "rate",
    "util",
    "usage",
    "cpu_used",
}

COUNT_PATTERNS: Final = {
    "count",
    "total",
    "num",
    "number",
    "items",
    "requests",
    "retransmit",
    "failed",
    "errors",
    "oom",
    "broken",
    "skipped",
}

MEMORY_PATTERNS: Final = {
    "rss",
    "memory",
    "mem",
    "kb",
    "mb",
    "bytes",
}

IPERF_PATTERNS: Final = {
    "iperf",
    "network_loopback",
}

STRESS_NG_PATTERNS: Final = {
    "stress_ng",
}

CHART_SCORE_RULES: tuple[tuple[str, int], ...] = (
    ("iperf", 140),
    ("network_loopback", 140),
    ("systemd", 130),
    ("bitrate", 120),
    ("bits_per_second", 120),
    ("bps", 120),
    ("bandwidth", 115),
    ("iops", 110),
    ("ops_per_sec", 105),
    ("ops_s", 105),
    ("bogo_ops", 100),
    ("pps", 95),
    ("latency", 90),
    ("clat", 88),
    ("slat", 86),
    ("rtt", 84),
    ("duration", 80),
    ("elapsed", 78),
    ("runtime", 76),
    ("seconds", 74),
    ("time", 70),
    ("rss", 65),
    ("memory", 65),
    ("retransmit", 60),
)


@dataclass(frozen=True)
class SheetRows:
    name: str
    headers: list[str]
    rows: list[list[Any]]


@dataclass(frozen=True)
class ExperimentInfo:
    experiment_id: str
    distro: str
    configuration_id: str
    description: str
    experiment_type: str
    started_at: str


@dataclass(frozen=True)
class ComparisonGroup:
    order: int
    group_id: str
    label: str
    short_label: str
    experiments: dict[str, ExperimentInfo]


@dataclass(frozen=True)
class DistributionStats:
    mean: float
    low: float
    q1: float
    q3: float
    high: float
    samples: int


@dataclass(frozen=True)
class ChartPoint:
    category: str
    poky: float | None
    suse: float | None
    poky_stats: DistributionStats | None = None
    suse_stats: DistributionStats | None = None


@dataclass(frozen=True)
class ChartSpec:
    chart_no: int
    logical_test: str
    source_sheet: str
    metric_name: str
    chart_kind: str
    y_axis_title: str
    reason: str
    points: tuple[ChartPoint, ...]


@dataclass
class MetricBucket:
    logical_test: str
    source_sheet: str
    metric_name: str
    values: dict[str, dict[str, list[float]]]


@dataclass(frozen=True)
class MetricWorksheetContext:
    sheet_name: str
    source_sheet: str
    rows: Iterator[tuple[Any, ...]]
    headers: list[str]
    config_index: int
    experiment_index: int
    metric_indexes: list[int]
    test_name_index: int | None
    tool_name_index: int | None
    util_type_index: int | None
    distribution_index: int | None


@dataclass(frozen=True)
class DistroComparisonExportOptions:
    output_path: Path | None = None
    experiment_ids: Sequence[str] | None = None
    latest_pair_only: bool = False
    max_charts: int = DEFAULT_MAX_CHARTS
    charts_per_sheet: int = DEFAULT_CHARTS_PER_SHEET
    copy_source_sheets: bool = False
    include_comparison: bool = True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build one Excel comparison report from report.xlsx. "
            "One chart is built per metric; each chart compares Poky and SUSE across the same runs."
        ),
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Existing report.xlsx generated by excel_export.py.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "Output .xlsx file or output directory. "
            "Default: input filename with _comparison suffix."
        ),
    )
    parser.add_argument(
        "--experiment-ids",
        nargs="+",
        help=(
            "Experiment IDs to compare. With two IDs, one Poky/SUSE group is created. "
            "With many IDs, comparable Poky/SUSE pairs are built inside the selected IDs."
        ),
    )
    parser.add_argument(
        "--latest-pair-only",
        action="store_true",
        help=(
            "Compare only the latest comparable Poky/SUSE pair. "
            "By default all comparable pairs are used."
        ),
    )
    parser.add_argument(
        "--max-charts",
        type=int,
        default=DEFAULT_MAX_CHARTS,
        help="Maximum number of charts. Use 0 to build all suitable charts. Default: 0.",
    )
    parser.add_argument(
        "--charts-per-sheet",
        type=int,
        default=DEFAULT_CHARTS_PER_SHEET,
        help="How many chart blocks to place on one chart sheet. Default: 30.",
    )
    parser.add_argument(
        "--copy-source-sheets",
        action="store_true",
        help=(
            "Also copy original source sheets into the output workbook. "
            "Off by default to keep the result readable."
        ),
    )
    parser.add_argument(
        "--no-comparison",
        action="store_false",
        dest="include_comparison",
        help="Copy source sheets only, do not build comparison tables/charts.",
    )
    parser.set_defaults(include_comparison=True)
    return parser.parse_args()


def build_report(
    input_path: Path,
    *,
    options: DistroComparisonExportOptions,
) -> Path:
    source_wb = load_workbook(input_path, read_only=True, data_only=True)
    source_sheets = read_source_sheets(source_wb) if should_copy_source_sheets(options) else []
    config_distro = build_configuration_distro_map(source_wb)
    experiment_info = build_experiment_info_map(source_wb, config_distro)

    groups: list[ComparisonGroup] = []
    chart_specs: list[ChartSpec] = []

    if options.include_comparison:
        groups = build_comparison_groups(
            experiment_info,
            experiment_ids=(
                list(options.experiment_ids) if options.experiment_ids is not None else None
            ),
            latest_pair_only=options.latest_pair_only,
        )
        logger.info("Comparable Poky/SUSE groups: %s", len(groups))
        if groups:
            buckets = extract_metric_buckets(source_wb, config_distro, groups)
            logger.info("Metric buckets with data: %s", len(buckets))
            chart_specs = build_chart_specs(buckets, groups, max_charts=options.max_charts)
            logger.info("Charts built: %s", len(chart_specs))

    result_wb = Workbook()
    result_wb.remove(result_wb.active)
    used_sheet_names: set[str] = set()

    if options.include_comparison:
        write_comparison_selection(result_wb, used_sheet_names, groups, len(chart_specs))
        write_comparison_index(result_wb, used_sheet_names, chart_specs)
        write_comparison_data(result_wb, used_sheet_names, chart_specs)
        write_comparison_charts(
            result_wb,
            used_sheet_names,
            chart_specs,
            charts_per_sheet=options.charts_per_sheet,
        )

    for sheet in source_sheets:
        if not sheet_has_data_rows(sheet):
            continue
        ws = result_wb.create_sheet(unique_sheet_name(sheet.name, used_sheet_names))
        write_table_sheet(ws, sheet)

    if not result_wb.worksheets:
        ws = result_wb.create_sheet("no_data")
        ws["A1"] = "No data found."

    result_path = resolve_output_path(input_path, options.output_path)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_wb.save(result_path)
    return result_path


def should_copy_source_sheets(options: DistroComparisonExportOptions) -> bool:
    return options.copy_source_sheets or not options.include_comparison


def export_distro_comparison_to_excel(
    input_path: Path,
    options: DistroComparisonExportOptions | None = None,
) -> Path:
    options = options or DistroComparisonExportOptions()
    return build_report(
        input_path=input_path,
        options=options,
    )


def read_source_sheets(workbook: Any) -> list[SheetRows]:
    sheets: list[SheetRows] = []
    for worksheet in workbook.worksheets:
        if is_comparison_sheet(worksheet.title):
            continue
        rows_iter = worksheet.iter_rows(values_only=True)
        try:
            headers = [normalize_header(value) for value in next(rows_iter)]
        except StopIteration:
            continue
        rows = [list(row) for row in rows_iter if row_has_data(row)]
        sheets.append(SheetRows(name=worksheet.title, headers=headers, rows=rows))
    return sheets


def is_comparison_sheet(sheet_name: str) -> bool:
    return sheet_name in SKIP_SOURCE_SHEETS or sheet_name.startswith(
        (f"{COMPARISON_CHARTS_PREFIX}_", f"{CHART_SHEET_PREFIX}_"),
    )


def build_configuration_distro_map(workbook: Any) -> dict[str, str]:
    if CONFIGURATION_SHEET not in workbook.sheetnames:
        return {}
    ws = workbook[CONFIGURATION_SHEET]
    rows = ws.iter_rows(values_only=True)
    try:
        headers = [normalize_header(value) for value in next(rows)]
    except StopIteration:
        return {}

    config_index = column_index(headers, "configuration_id")
    distro_index = column_index(headers, "distribution_description")
    if config_index is None or distro_index is None:
        return {}

    result: dict[str, str] = {}
    for row in rows:
        key = id_key(cell_value(row, config_index))
        distro = normalize_distro(cell_value(row, distro_index))
        if key and distro:
            result[key] = distro
    return result


def build_experiment_info_map(
    workbook: Any,
    config_distro: dict[str, str],
) -> dict[str, ExperimentInfo]:
    if EXPERIMENT_SHEET not in workbook.sheetnames:
        return {}
    ws = workbook[EXPERIMENT_SHEET]
    rows = ws.iter_rows(values_only=True)
    try:
        headers = [normalize_header(value) for value in next(rows)]
    except StopIteration:
        return {}

    config_index = column_index(headers, "configuration_id")
    experiment_index = column_index(headers, "experiment_id")
    description_index = column_index(headers, "description")
    type_index = column_index(headers, "type")
    started_at_index = column_index(headers, "started_at")
    if config_index is None or experiment_index is None:
        return {}

    result: dict[str, ExperimentInfo] = {}
    for row in rows:
        experiment_id = id_key(cell_value(row, experiment_index))
        configuration_id = id_key(cell_value(row, config_index))
        if not experiment_id:
            continue
        result[experiment_id] = ExperimentInfo(
            experiment_id=experiment_id,
            distro=config_distro.get(configuration_id, ""),
            configuration_id=configuration_id,
            description=str(cell_value(row, description_index) or "").strip(),
            experiment_type=str(cell_value(row, type_index) or "").strip(),
            started_at=str(cell_value(row, started_at_index) or "").strip(),
        )
    return result


def build_comparison_groups(
    experiment_info: dict[str, ExperimentInfo],
    *,
    experiment_ids: list[str] | None,
    latest_pair_only: bool,
) -> list[ComparisonGroup]:
    selected_ids = normalize_selected_ids(experiment_ids)

    if selected_ids and len(selected_ids) == EXPLICIT_PAIR_EXPERIMENT_COUNT:
        infos = [
            experiment_info.get(experiment_id)
            for experiment_id in sorted(selected_ids, key=sortable_value)
        ]
        if not all(infos):
            missing = [
                experiment_id
                for experiment_id, info in zip(sorted(selected_ids), infos, strict=False)
                if info is None
            ]
            logger.warning("Experiment IDs not found in experiment sheet: %s", ", ".join(missing))
            return []
        by_distro = {
            info.distro: info for info in infos if info is not None and info.distro in DISTROS
        }
        if not all(distro in by_distro for distro in DISTROS):
            logger.warning(
                "Two IDs were provided, but they are not one Poky and one SUSE experiment.",
            )
            return []
        return [make_group(by_distro["poky"], by_distro["suse"], order=1)]

    filtered_infos = [
        info
        for info in experiment_info.values()
        if info.distro in DISTROS and (not selected_ids or info.experiment_id in selected_ids)
    ]
    grouped: dict[tuple[str, str], dict[str, list[ExperimentInfo]]] = defaultdict(
        lambda: defaultdict(list),
    )
    for info in filtered_infos:
        grouped[(info.description, info.experiment_type)][info.distro].append(info)

    groups: list[ComparisonGroup] = []
    order = 1
    for key in sorted(grouped, key=lambda item: (item[0], item[1])):
        by_distro = grouped[key]
        if not all(distro in by_distro for distro in DISTROS):
            continue
        poky_items = sorted(by_distro["poky"], key=experiment_sort_key)
        suse_items = sorted(by_distro["suse"], key=experiment_sort_key)
        for poky_info, suse_info in zip(poky_items, suse_items, strict=False):
            groups.append(make_group(poky_info, suse_info, order=order))
            order += 1

    if latest_pair_only and groups:
        return [
            max(
                groups,
                key=lambda group: max(
                    experiment_sort_key(info) for info in group.experiments.values()
                ),
            ),
        ]
    return groups


def make_group(
    poky_info: ExperimentInfo,
    suse_info: ExperimentInfo,
    *,
    order: int,
) -> ComparisonGroup:
    group_id = f"exp_{poky_info.experiment_id}_{suse_info.experiment_id}"
    label_parts = [part for part in (poky_info.description, poky_info.experiment_type) if part]
    base_label = " | ".join(label_parts) or "experiment"
    short_label = f"{order}: p{poky_info.experiment_id}/s{suse_info.experiment_id}"
    label = (
        f"{base_label} | exp {poky_info.experiment_id} / poky vs "
        f"exp {suse_info.experiment_id} / suse"
    )
    return ComparisonGroup(
        order=order,
        group_id=group_id,
        label=label,
        short_label=short_label,
        experiments={"poky": poky_info, "suse": suse_info},
    )


def normalize_selected_ids(experiment_ids: list[str] | None) -> set[str]:
    if not experiment_ids:
        return set()
    return {
        normalized_id
        for experiment_id in experiment_ids
        if (normalized_id := id_key(experiment_id))
    }


def experiment_sort_key(info: ExperimentInfo) -> tuple[str, tuple[int, int, str]]:
    return info.started_at, sortable_value(info.experiment_id)


def extract_metric_buckets(
    workbook: Any,
    config_distro: dict[str, str],
    groups: list[ComparisonGroup],
) -> list[MetricBucket]:
    group_by_experiment = build_group_by_experiment(groups)
    buckets: dict[tuple[str, str, str], MetricBucket] = {}

    for worksheet in workbook.worksheets:
        context = metric_worksheet_context(worksheet)
        if context is None:
            continue
        for row in context.rows:
            collect_metric_row(row, context, group_by_experiment, config_distro, buckets)

    return list(buckets.values())


def build_group_by_experiment(groups: list[ComparisonGroup]) -> dict[str, ComparisonGroup]:
    group_by_experiment: dict[str, ComparisonGroup] = {}
    for group in groups:
        for info in group.experiments.values():
            group_by_experiment[info.experiment_id] = group
    return group_by_experiment


def metric_worksheet_context(worksheet: Any) -> MetricWorksheetContext | None:
    sheet_name = worksheet.title
    if is_comparison_sheet(sheet_name):
        return None

    rows_iter = worksheet.iter_rows(values_only=True)
    try:
        headers = [normalize_header(value) for value in next(rows_iter)]
    except StopIteration:
        return None

    config_index = column_index(headers, "configuration_id")
    experiment_index = column_index(headers, "experiment_id")
    if config_index is None or experiment_index is None:
        return None

    metric_indexes = find_metric_columns(headers)
    if not metric_indexes:
        return None

    return MetricWorksheetContext(
        sheet_name=sheet_name,
        source_sheet=strip_excel_suffix(sheet_name),
        rows=rows_iter,
        headers=headers,
        config_index=config_index,
        experiment_index=experiment_index,
        metric_indexes=metric_indexes,
        test_name_index=column_index(headers, "test_name"),
        tool_name_index=column_index(headers, "tool_name"),
        util_type_index=column_index(headers, "util_type"),
        distribution_index=column_index(headers, "distribution_description"),
    )


def collect_metric_row(
    row: tuple[Any, ...],
    context: MetricWorksheetContext,
    group_by_experiment: dict[str, ComparisonGroup],
    config_distro: dict[str, str],
    buckets: dict[tuple[str, str, str], MetricBucket],
) -> None:
    experiment_id = id_key(cell_value(row, context.experiment_index))
    group = group_by_experiment.get(experiment_id)
    if group is None:
        return

    distro = row_distro(row, context.distribution_index, context.config_index, config_distro)
    if distro not in DISTROS:
        return

    logical_test = logical_test_name(
        context.sheet_name,
        cell_value(row, context.test_name_index),
        cell_value(row, context.tool_name_index),
        cell_value(row, context.util_type_index),
    )

    for metric_index in context.metric_indexes:
        metric_name = context.headers[metric_index]
        value = to_finite_float(cell_value(row, metric_index))
        if value is None or is_invalid_metric_value(value) or not is_nonzero_number(value):
            continue
        bucket = get_or_create_metric_bucket(
            buckets,
            logical_test,
            context.source_sheet,
            metric_name,
        )
        bucket.values[group.group_id][distro].append(value)


def get_or_create_metric_bucket(
    buckets: dict[tuple[str, str, str], MetricBucket],
    logical_test: str,
    source_sheet: str,
    metric_name: str,
) -> MetricBucket:
    bucket_key = (logical_test, source_sheet, metric_name)
    bucket = buckets.get(bucket_key)
    if bucket is None:
        bucket = MetricBucket(
            logical_test=logical_test,
            source_sheet=source_sheet,
            metric_name=metric_name,
            values=defaultdict(lambda: defaultdict(list)),
        )
        buckets[bucket_key] = bucket
    return bucket


def find_metric_columns(headers: list[str]) -> list[int]:
    metric_indexes: list[int] = []
    for index, header in enumerate(headers):
        if not header or header in LABEL_COLUMNS:
            continue
        normalized_header = normalize_metric_text(header)
        if not normalized_header:
            continue
        tokens = set(normalized_header.split("_"))
        if tokens & TECHNICAL_TOKENS:
            continue
        metric_indexes.append(index)
    return metric_indexes


def row_distro(
    row: tuple[Any, ...],
    distribution_index: int | None,
    config_index: int,
    config_distro: dict[str, str],
) -> str:
    if distribution_index is not None:
        distro = normalize_distro(cell_value(row, distribution_index))
        if distro:
            return distro
    return config_distro.get(id_key(cell_value(row, config_index)), "")


def logical_test_name(sheet_name: str, test_name: Any, tool_name: Any, util_type: Any) -> str:
    parts: list[str] = []
    prepared_test_name = str(test_name or "").strip()
    prepared_tool_name = str(tool_name or "").strip()
    prepared_util_type = str(util_type or "").strip()

    if prepared_test_name:
        parts.append(prepared_test_name)
    else:
        parts.append(strip_excel_suffix(sheet_name))

    if prepared_tool_name and prepared_tool_name.lower() not in prepared_test_name.lower():
        parts.append(prepared_tool_name)
    if prepared_util_type:
        parts.append(prepared_util_type)
    return " / ".join(parts)


def strip_excel_suffix(sheet_name: str) -> str:
    return re.sub(r"_\d+$", "", str(sheet_name).strip())


def build_chart_specs(
    buckets: list[MetricBucket],
    groups: list[ComparisonGroup],
    *,
    max_charts: int,
) -> list[ChartSpec]:
    candidates: list[tuple[int, str, ChartSpec]] = []

    for bucket in buckets:
        points: list[ChartPoint] = []
        for group in groups:
            values_by_distro = bucket.values.get(group.group_id, {})
            poky_stats = distribution_stats_or_none(values_by_distro.get("poky", []))
            suse_stats = distribution_stats_or_none(values_by_distro.get("suse", []))
            if poky_stats is not None and suse_stats is not None:
                points.append(
                    ChartPoint(
                        category=group.short_label,
                        poky=poky_stats.mean,
                        suse=suse_stats.mean,
                        poky_stats=poky_stats,
                        suse_stats=suse_stats,
                    ),
                )

        if not points:
            continue

        chart_kind, y_axis_title, reason = choose_chart_style(bucket, points)
        chart = ChartSpec(
            chart_no=0,
            logical_test=bucket.logical_test,
            source_sheet=bucket.source_sheet,
            metric_name=bucket.metric_name,
            chart_kind=chart_kind,
            y_axis_title=y_axis_title,
            reason=reason,
            points=tuple(points),
        )
        score = chart_score(bucket, len(points))
        sort_key = f"{bucket.logical_test}|{bucket.source_sheet}|{bucket.metric_name}"
        candidates.append((score, sort_key, chart))

    candidates.sort(key=lambda item: (-item[0], item[1]))
    if max_charts > 0:
        candidates = candidates[:max_charts]

    result: list[ChartSpec] = []
    for chart_no, (_, _, chart) in enumerate(candidates, start=1):
        result.append(
            ChartSpec(
                chart_no=chart_no,
                logical_test=chart.logical_test,
                source_sheet=chart.source_sheet,
                metric_name=chart.metric_name,
                chart_kind=chart.chart_kind,
                y_axis_title=chart.y_axis_title,
                reason=chart.reason,
                points=chart.points,
            ),
        )
    return result


def choose_chart_style(bucket: MetricBucket, points: list[ChartPoint]) -> tuple[str, str, str]:
    points_count = len(points)
    text = normalize_metric_text(
        f"{bucket.logical_test} {bucket.source_sheet} {bucket.metric_name}",
    )
    tokens = set(text.split("_"))
    y_axis_title = y_axis_title_for(text, tokens)

    if is_iperf_test_bucket(bucket):
        style = (
            "candlestick",
            y_axis_title,
            "iperf metrics are shown as candlestick charts",
        )
    elif is_stress_ng_bucket(bucket):
        style = trend_chart_style(
            points_count,
            y_axis_title,
            (
                "stress-ng metrics are compared consistently inside one test type "
                "by run-to-run trend"
            ),
        )
    elif metric_has_any_pattern(text, tokens, {"systemd", "systemd_analyze"}):
        style = (
            "histogram",
            "Mean time, sec; lower is better",
            (
                "systemd-analyze is a set of boot-time scalar values, so grouped "
                "columns compare Poky and SUSE directly"
            ),
        )
    elif metric_has_any_pattern(text, tokens, COUNT_PATTERNS):
        style = (
            "column",
            "Mean count",
            (
                "count/error metrics are discrete scalar values, so grouped columns "
                "make Poky/SUSE differences easy to read"
            ),
        )
    elif metric_has_any_pattern(text, tokens, MEMORY_PATTERNS):
        style = trend_chart_style(
            points_count,
            "Mean memory/size",
            "memory/size metrics are compared by mean values across comparable runs",
        )
    elif metric_has_any_pattern(
        text,
        tokens,
        THROUGHPUT_PATTERNS | PERCENT_PATTERNS | TIME_PATTERNS,
    ):
        style = trend_chart_style(
            points_count,
            y_axis_title,
            "this metric is compared by mean values across comparable runs",
        )
    else:
        style = trend_chart_style(
            points_count,
            y_axis_title,
            "generic scalar metric comparison by mean values",
        )
    return style


def trend_chart_style(points_count: int, y_axis_title: str, reason: str) -> tuple[str, str, str]:
    if points_count >= MIN_TREND_POINTS:
        return ("line", y_axis_title, reason)
    return ("column", y_axis_title, reason)


def y_axis_title_for(text: str, tokens: set[str]) -> str:
    if metric_has_any_pattern(text, tokens, PERCENT_PATTERNS):
        return "Mean, % / ratio"
    if metric_has_any_pattern(text, tokens, THROUGHPUT_PATTERNS):
        return "Mean throughput; higher is better"
    if metric_has_any_pattern(text, tokens, TIME_PATTERNS):
        return "Mean time; lower is better"
    if metric_has_any_pattern(text, tokens, MEMORY_PATTERNS):
        return "Mean memory/size"
    if metric_has_any_pattern(text, tokens, COUNT_PATTERNS):
        return "Mean count"
    return "Mean"


def chart_score(bucket: MetricBucket, points_count: int) -> int:
    text = normalize_metric_text(
        f"{bucket.logical_test} {bucket.source_sheet} {bucket.metric_name}",
    )
    tokens = set(text.split("_"))
    score = 0
    for pattern, pattern_score in CHART_SCORE_RULES:
        if pattern in IPERF_PATTERNS and not is_iperf_test_bucket(bucket):
            continue
        if metric_matches(text, tokens, pattern):
            score = max(score, pattern_score)
    if points_count >= MIN_TREND_POINTS:
        score += 10
    return score


def is_iperf_test_bucket(bucket: MetricBucket) -> bool:
    test_text = normalize_metric_text(f"{bucket.logical_test} {bucket.source_sheet}")
    test_tokens = set(test_text.split("_"))
    return metric_has_any_pattern(test_text, test_tokens, IPERF_PATTERNS)


def is_stress_ng_bucket(bucket: MetricBucket) -> bool:
    test_text = normalize_metric_text(f"{bucket.logical_test} {bucket.source_sheet}")
    test_tokens = set(test_text.split("_"))
    return metric_has_any_pattern(test_text, test_tokens, STRESS_NG_PATTERNS)


def write_comparison_selection(
    workbook: Workbook,
    used_sheet_names: set[str],
    groups: list[ComparisonGroup],
    chart_count: int,
) -> None:
    ws = workbook.create_sheet(unique_sheet_name(COMPARISON_SELECTION_SHEET, used_sheet_names))
    rows: list[list[Any]] = [
        [
            "group_order",
            "group_id",
            "group_label",
            "short_label",
            "experiment_order",
            "experiment_id",
            "distro",
            "configuration_id",
            "description",
            "type",
            "started_at",
        ],
    ]
    for group in groups:
        for experiment_order, distro in enumerate(DISTROS, start=1):
            info = group.experiments[distro]
            rows.append(
                [
                    group.order,
                    group.group_id,
                    group.label,
                    group.short_label,
                    experiment_order,
                    info.experiment_id,
                    info.distro,
                    info.configuration_id,
                    info.description,
                    info.experiment_type,
                    info.started_at,
                ],
            )
    rows.append([])
    rows.append(["charts_built", chart_count, None, None, None, None, None, None, None, None, None])
    write_matrix(ws, rows)
    style_table(ws, len(rows), len(rows[0]))
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def write_comparison_index(
    workbook: Workbook,
    used_sheet_names: set[str],
    charts: list[ChartSpec],
) -> None:
    ws = workbook.create_sheet(unique_sheet_name(COMPARISON_INDEX_SHEET, used_sheet_names))
    rows: list[list[Any]] = [
        [
            "chart_no",
            "title",
            "test_type",
            "test_name",
            "metric_name",
            "points",
        ],
    ]
    rows.extend(
        [
            chart.chart_no,
            chart_title(chart),
            chart.source_sheet,
            chart.logical_test,
            chart.metric_name,
            len(chart.points),
        ]
        for chart in charts
    )
    write_matrix(ws, rows)
    style_table(ws, len(rows), len(rows[0]))
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def write_comparison_data(
    workbook: Workbook,
    used_sheet_names: set[str],
    charts: list[ChartSpec],
) -> None:
    ws = workbook.create_sheet(unique_sheet_name(COMPARISON_DATA_SHEET, used_sheet_names))
    rows: list[list[Any]] = [
        [
            "chart_no",
            "logical_test",
            "source_sheet",
            "metric_name",
            "category",
            "poky",
            "suse",
        ],
    ]
    rows.extend(
        [
            chart.chart_no,
            chart.logical_test,
            chart.source_sheet,
            chart.metric_name,
            point.category,
            point.poky,
            point.suse,
        ]
        for chart in charts
        for point in chart.points
    )
    write_matrix(ws, rows)
    style_table(ws, len(rows), len(rows[0]))
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def write_comparison_charts(
    workbook: Workbook,
    used_sheet_names: set[str],
    charts: list[ChartSpec],
    *,
    charts_per_sheet: int,
) -> None:
    if not charts:
        return

    charts_per_sheet = max(1, charts_per_sheet)
    charts_by_test_type = group_charts_by_test_type(charts)
    for test_type, test_type_charts in charts_by_test_type.items():
        for start in range(0, len(test_type_charts), charts_per_sheet):
            sheet_number = start // charts_per_sheet + 1
            sheet_name = chart_sheet_name(test_type, sheet_number)
            ws = workbook.create_sheet(unique_sheet_name(sheet_name, used_sheet_names))
            setup_chart_sheet(ws)
            current_row = 1
            for chart in test_type_charts[start : start + charts_per_sheet]:
                write_chart_block(ws, current_row, chart)
                current_row += max(chart_block_height(chart), 24)


def group_charts_by_test_type(charts: list[ChartSpec]) -> dict[str, list[ChartSpec]]:
    grouped: dict[str, list[ChartSpec]] = {}
    for chart in charts:
        test_type = chart.source_sheet or "test"
        grouped.setdefault(test_type, []).append(chart)
    return grouped


def chart_sheet_name(test_type: str, sheet_number: int) -> str:
    base_name = f"{CHART_SHEET_PREFIX}_{test_type or 'test'}"
    suffix = f"_{sheet_number}" if sheet_number > 1 else ""
    cleaned_base = sanitize_sheet_name(base_name)
    if suffix:
        return f"{cleaned_base[: 31 - len(suffix)]}{suffix}"
    return cleaned_base


def chart_block_height(chart: ChartSpec) -> int:
    row_count = (
        len(candlestick_rows(chart)) if chart.chart_kind == "candlestick" else len(chart.points)
    )
    return max(row_count + 8, 24)


def setup_chart_sheet(ws: Any) -> None:
    widths = {
        "A": 24,
        "B": 18,
        "C": 18,
        "D": 18,
        "E": 18,
        "F": 18,
        "G": 18,
        "H": 18,
        "I": 18,
        "J": 18,
    }
    for column, width in widths.items():
        ws.column_dimensions[column].width = width


def write_chart_block(ws: Any, start_row: int, chart: ChartSpec) -> None:
    if chart.chart_kind == "candlestick":
        write_candlestick_chart_block(ws, start_row, chart)
        return

    title = chart_title(chart)
    title_cell = ws.cell(row=start_row, column=1, value=title)
    title_cell.font = Font(bold=True, size=12)

    header_row = start_row + 2
    headers = ["run", "poky", "suse"]
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=col, value=header)
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="D9EAF7")

    data_start = header_row + 1
    for offset, point in enumerate(chart.points):
        row = data_start + offset
        ws.cell(row=row, column=1, value=point.category)
        ws.cell(row=row, column=2, value=point.poky)
        ws.cell(row=row, column=3, value=point.suse)

    data_end = data_start + len(chart.points) - 1
    excel_chart = build_excel_chart(chart)
    excel_chart.add_data(
        Reference(ws, min_col=2, min_row=header_row, max_col=3, max_row=data_end),
        titles_from_data=True,
    )
    excel_chart.set_categories(Reference(ws, min_col=1, min_row=data_start, max_row=data_end))
    ws.add_chart(excel_chart, f"E{start_row}")


def write_candlestick_chart_block(ws: Any, start_row: int, chart: ChartSpec) -> None:
    title = chart_title(chart)
    title_cell = ws.cell(row=start_row, column=1, value=title)
    title_cell.font = Font(bold=True, size=12)

    header_row = start_row + 2
    headers = ["run_distro", "open_q1", "high_max", "low_min", "close_q3", "mean", "samples"]
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=col, value=header)
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="D9EAF7")

    rows = candlestick_rows(chart)
    data_start = header_row + 1
    for offset, row_values in enumerate(rows):
        row = data_start + offset
        for col, value in enumerate(row_values, start=1):
            ws.cell(row=row, column=col, value=value)

    data_end = data_start + len(rows) - 1
    excel_chart = build_excel_chart(chart)
    excel_chart.add_data(
        Reference(ws, min_col=2, min_row=header_row, max_col=5, max_row=data_end),
        titles_from_data=True,
    )
    excel_chart.set_categories(Reference(ws, min_col=1, min_row=data_start, max_row=data_end))
    style_candlestick_excel_chart(excel_chart)
    ws.add_chart(excel_chart, f"I{start_row}")


def candlestick_rows(chart: ChartSpec) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for point in chart.points:
        if point.poky_stats is not None:
            rows.append(candlestick_row(f"{point.category} poky", point.poky_stats))
        if point.suse_stats is not None:
            rows.append(candlestick_row(f"{point.category} suse", point.suse_stats))
    return rows


def candlestick_row(label: str, stats: DistributionStats) -> list[Any]:
    return [label, stats.q1, stats.high, stats.low, stats.q3, stats.mean, stats.samples]


def build_excel_chart(chart: ChartSpec) -> BarChart | LineChart | AreaChart | StockChart:
    if chart.chart_kind == "line":
        excel_chart = LineChart()
    elif chart.chart_kind == "area":
        excel_chart = AreaChart()
    elif chart.chart_kind == "candlestick":
        excel_chart = StockChart()
        excel_chart.hiLowLines = ChartLines()
        excel_chart.upDownBars = UpDownBars()
    else:
        excel_chart = BarChart()
        excel_chart.type = "bar" if chart.chart_kind == "bar" else "col"
        excel_chart.grouping = "clustered"
        excel_chart.overlap = 0

    excel_chart.title = chart_title(chart)[:255]
    excel_chart.y_axis.title = chart.y_axis_title
    excel_chart.x_axis.title = "Run"
    excel_chart.height = 8
    excel_chart.width = 18
    if should_show_legend(chart):
        excel_chart.legend.position = "r"
    else:
        excel_chart.legend = None
    return excel_chart


def should_show_legend(chart: ChartSpec) -> bool:
    return chart.chart_kind != "candlestick"


def style_candlestick_excel_chart(excel_chart: StockChart) -> None:
    for series in excel_chart.series:
        series.graphicalProperties.line.noFill = True
        series.graphicalProperties.noFill = True
        if series.marker is not None:
            series.marker.symbol = "none"
            series.marker.graphicalProperties.line.noFill = True
            series.marker.graphicalProperties.noFill = True


def chart_title(chart: ChartSpec) -> str:
    test_type = str(chart.source_sheet or "test").strip()
    test_name = str(chart.logical_test or "test").strip()
    metric_name = str(chart.metric_name or "metric").strip()

    if normalize_metric_text(test_type) == normalize_metric_text(test_name):
        return f"{test_type}: {metric_name}"

    return f"{test_type} ({test_name}): {metric_name}"


def write_table_sheet(ws: Any, sheet: SheetRows) -> None:
    rows = [sheet.headers, *sheet.rows]
    write_matrix(ws, rows)
    style_table(ws, len(rows), len(sheet.headers))
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def write_matrix(ws: Any, rows: list[list[Any]]) -> None:
    for row in rows:
        ws.append(list(row))


def style_table(ws: Any, row_count: int, col_count: int) -> None:
    if row_count <= 0 or col_count <= 0:
        return
    header_fill = PatternFill("solid", fgColor="D9EAF7")
    for col in range(1, col_count + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = Font(bold=True)
        cell.fill = header_fill
        width = min(max(len(str(cell.value or "")) + 2, 12), 45)
        ws.column_dimensions[cell.column_letter].width = width
    for row in ws.iter_rows(min_row=2, max_row=min(row_count, 200), max_col=col_count):
        for cell in row:
            if isinstance(cell.value, float):
                cell.number_format = "0.000"


def resolve_output_path(input_path: Path, output_path: Path | None) -> Path:
    if output_path is None:
        return input_path.with_name(
            f"{input_path.stem}_{COMPARISON_OUTPUT_NAME}{input_path.suffix}",
        )
    if output_path.suffix.lower() == ".xlsx":
        return output_path
    return output_path / f"{input_path.stem}_{COMPARISON_OUTPUT_NAME}.xlsx"


def normalize_header(value: Any) -> str:
    return "" if value is None else str(value).strip()


def column_index(headers: list[str], name: str) -> int | None:
    for index, header in enumerate(headers):
        if header == name:
            return index
    return None


def cell_value(row: tuple[Any, ...] | list[Any], index: int | None) -> Any:
    if index is None or index >= len(row):
        return None
    return row[index]


def row_has_data(row: tuple[Any, ...] | list[Any]) -> bool:
    return any(not is_empty_value(value) for value in row)


def sheet_has_data_rows(sheet: SheetRows) -> bool:
    return any(row_has_data(row) for row in sheet.rows)


def is_empty_value(value: Any) -> bool:
    return value is None or value == ""


def id_key(value: Any) -> str:
    if isinstance(value, bool) or value is None:
        return ""
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def normalize_distro(value: Any) -> str:
    text = str(value or "").strip().lower()
    if "suse" in text:
        return "suse"
    if "yocto" in text or "poky" in text:
        return "poky"
    return text


def normalize_metric_text(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", str(value).lower())
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("_")


def metric_matches(metric_text: str, metric_tokens: set[str], pattern: str) -> bool:
    if len(pattern) <= SHORT_TOKEN_LENGTH:
        return pattern in metric_tokens
    return pattern in metric_text


def metric_has_any_pattern(metric_text: str, metric_tokens: set[str], patterns: set[str]) -> bool:
    return any(metric_matches(metric_text, metric_tokens, pattern) for pattern in patterns)


def sortable_value(value: Any) -> tuple[int, int, str]:
    text = str(value or "").strip()
    try:
        return (0, int(text), "")
    except ValueError:
        return (1, 0, text)


def to_finite_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        converted = float(value)
        return converted if math.isfinite(converted) else None
    if isinstance(value, str):
        prepared = value.strip().replace(",", ".")
        if not prepared:
            return None
        try:
            converted = float(prepared)
        except ValueError:
            return None
        return converted if math.isfinite(converted) else None
    return None


def is_nonzero_number(value: float | None) -> bool:
    return value is not None and abs(value) > NONZERO_EPSILON


def is_invalid_metric_value(value: float) -> bool:
    return value in INVALID_NUMERIC_SENTINELS


def distribution_stats_or_none(values: list[float]) -> DistributionStats | None:
    prepared = sorted(value for value in values if is_nonzero_number(value))
    if not prepared:
        return None
    return DistributionStats(
        mean=statistics.fmean(prepared),
        low=prepared[0],
        q1=percentile(prepared, 0.25),
        q3=percentile(prepared, 0.75),
        high=prepared[-1],
        samples=len(prepared),
    )


def percentile(sorted_values: list[float], fraction: float) -> float:
    if not sorted_values:
        msg = "Cannot calculate percentile for an empty list."
        raise ValueError(msg)
    if len(sorted_values) == 1:
        return sorted_values[0]

    position = (len(sorted_values) - 1) * fraction
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return sorted_values[lower_index]

    lower_value = sorted_values[lower_index]
    upper_value = sorted_values[upper_index]
    weight = position - lower_index
    return lower_value + (upper_value - lower_value) * weight


def unique_sheet_name(name: str, used_names: set[str]) -> str:
    cleaned = sanitize_sheet_name(name)
    original = cleaned
    suffix = 1
    while cleaned in used_names:
        suffix_text = f"_{suffix}"
        cleaned = f"{original[: 31 - len(suffix_text)]}{suffix_text}"
        suffix += 1
    used_names.add(cleaned)
    return cleaned


def sanitize_sheet_name(name: str) -> str:
    cleaned = "".join("_" if char in r":\/?*[]" else char for char in str(name)).strip("'")
    return (cleaned or "Sheet")[:31]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = parse_args()
    output_path = export_distro_comparison_to_excel(
        input_path=args.input,
        options=DistroComparisonExportOptions(
            output_path=args.output,
            experiment_ids=args.experiment_ids,
            latest_pair_only=args.latest_pair_only,
            max_charts=args.max_charts,
            charts_per_sheet=args.charts_per_sheet,
            copy_source_sheets=args.copy_source_sheets,
            include_comparison=args.include_comparison,
        ),
    )
    logger.info("Exported XLSX file: %s", output_path)


if __name__ == "__main__":
    main()
