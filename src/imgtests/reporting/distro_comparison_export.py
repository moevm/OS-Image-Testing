from __future__ import annotations

import logging
import math
import statistics
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from openpyxl import Workbook, load_workbook
from openpyxl.chart import AreaChart, BarChart, LineChart, Reference, StockChart
from openpyxl.chart.axis import ChartLines
from openpyxl.chart.updown_bars import UpDownBars
from openpyxl.styles import Font, PatternFill

from imgtests.reporting.distro_comparison_common import (
    CHART_SHEET_PREFIX,
    COMPARISON_DATA_SHEET,
    COMPARISON_INDEX_SHEET,
    COMPARISON_SELECTION_SHEET,
    COUNT_PATTERNS,
    DISTROS,
    IPERF_PATTERNS,
    MAX_SHEET_NAME_LENGTH,
    MEMORY_PATTERNS,
    PERCENT_PATTERNS,
    STRESS_NG_PATTERNS,
    THROUGHPUT_PATTERNS,
    TIME_PATTERNS,
    ComparisonGroup,
    MetricBucket,
    MetricExtractionOptions,
    SheetRows,
    build_comparison_groups,
    build_configuration_distro_map,
    build_experiment_info_map,
    find_metric_columns,
    is_comparison_sheet,
    is_nonzero_number,
    metric_has_any_pattern,
    metric_matches,
    normalize_header,
    normalize_metric_text,
    row_has_data,
    sanitize_sheet_name,
    sheet_has_data_rows,
    style_table,
    unique_sheet_name,
    write_matrix,
)
from imgtests.reporting.distro_comparison_common import (
    extract_metric_buckets as extract_common_metric_buckets,
)
from imgtests.reporting.distro_comparison_common import (
    resolve_output_path as resolve_common_output_path,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from openpyxl.worksheet.worksheet import Worksheet

logger = logging.getLogger(__name__)

COMPARISON_OUTPUT_NAME: Final = "comparison"

DEFAULT_MAX_CHARTS: Final = 0
DEFAULT_CHARTS_PER_SHEET: Final = 30
MIN_TREND_POINTS: Final = 3

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


@dataclass(frozen=True)
class DistroComparisonExportOptions:
    output_path: Path | None = None
    experiment_ids: Sequence[str] | None = None
    max_charts: int = DEFAULT_MAX_CHARTS
    charts_per_sheet: int = DEFAULT_CHARTS_PER_SHEET
    copy_source_sheets: bool = False
    include_comparison: bool = True


def build_report(
    input_path: Path,
    *,
    options: DistroComparisonExportOptions,
) -> Path:
    source_wb = load_workbook(input_path, read_only=True, data_only=True)
    try:
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
            )
            logger.info("Comparable Poky/SUSE groups: %s", len(groups))
            if groups:
                buckets = extract_metric_buckets(source_wb, config_distro, groups)
                logger.info("Metric buckets with data: %s", len(buckets))
                chart_specs = build_chart_specs(buckets, groups, max_charts=options.max_charts)
                logger.info("Charts built: %s", len(chart_specs))
    finally:
        source_wb.close()

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

    result_path = resolve_common_output_path(
        input_path,
        options.output_path,
        COMPARISON_OUTPUT_NAME,
    )
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


def read_source_sheets(workbook: Workbook) -> list[SheetRows]:
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


def extract_metric_buckets(
    workbook: Any,
    config_distro: dict[str, str],
    groups: list[ComparisonGroup],
) -> list[MetricBucket]:
    return extract_common_metric_buckets(
        workbook,
        config_distro,
        groups,
        MetricExtractionOptions(column_selector=find_metric_columns),
    )


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
    rows.append(["charts_built", chart_count] + [None] * 9)
    write_styled_table(ws, rows)


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
    write_styled_table(ws, rows)


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
    write_styled_table(ws, rows)


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
        return f"{cleaned_base[: MAX_SHEET_NAME_LENGTH - len(suffix)]}{suffix}"
    return cleaned_base


def chart_block_height(chart: ChartSpec) -> int:
    row_count = (
        len(candlestick_rows(chart)) if chart.chart_kind == "candlestick" else len(chart.points)
    )
    return max(row_count + 8, 24)


def setup_chart_sheet(ws: Worksheet) -> None:
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


def write_chart_block(ws: Worksheet, start_row: int, chart: ChartSpec) -> None:
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


def write_candlestick_chart_block(ws: Worksheet, start_row: int, chart: ChartSpec) -> None:
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


def write_table_sheet(ws: Worksheet, sheet: SheetRows) -> None:
    rows = [sheet.headers, *sheet.rows]
    write_styled_table(ws, rows)


def write_styled_table(ws: Worksheet, rows: list[list[Any]]) -> None:
    write_matrix(ws, rows)
    if not rows or not rows[0]:
        return
    style_table(ws, len(rows), len(rows[0]))
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


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
