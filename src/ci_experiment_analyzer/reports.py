"""Generate CI experiment reports."""

import csv
import json
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

from ci_experiment_analyzer.models import (
    AnalysisResult,
    BottleneckCandidateResult,
    ComparisonResult,
    LocalTotalImpactResult,
    MetricComparisonResult,
    MetricStats,
    ParallelAnalysisResult,
    ParallelMetricStats,
    ParallelRunMetrics,
    ParallelScenarioResult,
    ScenarioResult,
)


@dataclass(frozen=True, slots=True)
class AnalysisReportPaths:
    """Paths of generated experiment report files."""

    analysis_json: Path
    summary_csv: Path
    report_markdown: Path


_COMPARISON_SUMMARY_COLUMNS = (
    "analysis_type",
    "analysis_id",
    "baseline_scenario",
    "candidate_scenario",
    "source_metric_id",
    "metric_id",
    "unit",
    "baseline_median",
    "candidate_median",
    "absolute_difference",
    "relative_difference_percent",
)


def _format_report_number(
    value: float,
) -> str:
    """Format a report number without unstable trailing zeros."""
    if value == 0.0:
        return "0"

    return f"{value:.6f}".rstrip("0").rstrip(".")


def _format_report_percent(
    value: float | None,
) -> str:
    """Format an optional percentage for a human-readable report."""
    if value is None:
        return "N/A"

    return f"{_format_report_number(value)}%"


def _format_report_boolean(
    value: bool | None,
) -> str:
    """Format an optional boolean for a human-readable report."""
    if value is None:
        return "N/A"

    return "yes" if value else "no"


def _escape_markdown_cell(
    value: str,
) -> str:
    """Escape text used inside a Markdown table cell."""
    return (
        value.replace("\n", " ")
        .replace("|", r"\|")
    )


def _markdown_table(
    headers: tuple[str, ...],
    rows: tuple[tuple[str, ...], ...],
) -> list[str]:
    """Render a deterministic Markdown table."""
    header_line = "| " + " | ".join(headers) + " |"
    separator_line = (
        "| "
        + " | ".join("---" for _ in headers)
        + " |"
    )

    lines = [
        header_line,
        separator_line,
    ]

    lines.extend(
        "| " + " | ".join(row) + " |"
        for row in rows
    )

    return lines


def _analysis_warnings(
    result: AnalysisResult,
) -> tuple[str, ...]:
    """Collect interpretation and data-consistency warnings."""
    warnings: list[str] = []

    for impact in result.local_total_impacts:
        if impact.warning is not None:
            warnings.append(
                f"Comparison {impact.comparison_id!r}: "
                f"{impact.warning}"
            )

    for analysis in result.parallel_analyses:
        parallel_scenarios = (
            ("baseline", analysis.baseline),
            ("candidate", analysis.candidate),
        )

        for scenario_role, scenario in parallel_scenarios:
            if scenario.branch_count_consistent:
                continue

            warnings.append(
                f"Parallel analysis {analysis.analysis_id!r}, "
                f"{scenario_role} scenario "
                f"{scenario.scenario_id!r}: branch count "
                f"varies from "
                f"{scenario.branch_count_minimum} to "
                f"{scenario.branch_count_maximum}."
            )

    return tuple(warnings)


def _metric_stats_to_dict(
    metric: MetricStats,
) -> dict[str, object]:
    """Convert scenario metric statistics to a JSON-compatible mapping."""
    return {
        "id": metric.metric_id,
        "unit": metric.unit,
        "role": metric.role,
        "count": metric.count,
        "median": metric.median,
        "mean": metric.mean,
        "minimum": metric.minimum,
        "maximum": metric.maximum,
        "standard_deviation": metric.standard_deviation,
    }


def _scenario_result_to_dict(
    scenario: ScenarioResult,
) -> dict[str, object]:
    """Convert one scenario result to a JSON-compatible mapping."""
    return {
        "id": scenario.scenario_id,
        "metrics": [
            _metric_stats_to_dict(metric)
            for metric in scenario.metrics
        ],
    }


def _metric_comparison_to_dict(
    metric: MetricComparisonResult,
) -> dict[str, object]:
    """Convert one metric comparison to a JSON-compatible mapping."""
    return {
        "id": metric.metric_id,
        "unit": metric.unit,
        "baseline_median": metric.baseline_median,
        "candidate_median": metric.candidate_median,
        "absolute_difference": metric.absolute_difference,
        "relative_difference_percent": (
            metric.relative_difference_percent
        ),
    }


def _comparison_result_to_dict(
    comparison: ComparisonResult,
) -> dict[str, object]:
    """Convert one scenario comparison to a JSON-compatible mapping."""
    return {
        "id": comparison.comparison_id,
        "baseline": comparison.baseline_scenario_id,
        "candidate": comparison.candidate_scenario_id,
        "metrics": [
            _metric_comparison_to_dict(metric)
            for metric in comparison.metrics
        ],
    }


def _local_total_impact_to_dict(
    impact: LocalTotalImpactResult,
) -> dict[str, object]:
    """Convert one local-versus-total result to a report mapping."""
    return {
        "comparison": impact.comparison_id,
        "phase_metric": impact.phase_metric_id,
        "total_metric": impact.total_metric_id,
        "phase_relative_difference_percent": (
            impact.phase_relative_difference_percent
        ),
        "total_relative_difference_percent": (
            impact.total_relative_difference_percent
        ),
        "local_improvement_threshold_pct": (
            impact.local_improvement_threshold_pct
        ),
        "total_impact_threshold_pct": (
            impact.total_impact_threshold_pct
        ),
        "substantial_local_improvement": (
            impact.substantial_local_improvement
        ),
        "limited_total_improvement": (
            impact.limited_total_improvement
        ),
        "limited_end_to_end_impact": (
            impact.limited_end_to_end_impact
        ),
        "warning": impact.warning,
    }


def _bottleneck_candidate_to_dict(
    candidate: BottleneckCandidateResult,
) -> dict[str, object]:
    """Convert one bottleneck candidate to a report mapping."""
    return {
        "scenario": candidate.scenario_id,
        "phase_metrics": list(
            candidate.phase_metric_ids
        ),
        "median": candidate.median,
        "unit": candidate.unit,
        "is_tie": candidate.is_tie,
    }


def _parallel_metric_stats_to_dict(
    stats: ParallelMetricStats,
) -> dict[str, object]:
    """Convert parallel metric statistics to a report mapping."""
    return {
        "count": stats.count,
        "median": stats.median,
        "mean": stats.mean,
        "minimum": stats.minimum,
        "maximum": stats.maximum,
        "standard_deviation": stats.standard_deviation,
    }


def _parallel_run_metrics_to_dict(
    run: ParallelRunMetrics,
) -> dict[str, object]:
    """Convert one parallel run result to a report mapping."""
    return {
        "run_id": run.run_id,
        "branch_count": run.branch_count,
        "critical_path_duration": (
            run.critical_path_duration
        ),
        "minimum_branch_duration": (
            run.minimum_branch_duration
        ),
        "mean_branch_duration": (
            run.mean_branch_duration
        ),
        "spread": run.spread,
        "imbalance_ratio": run.imbalance_ratio,
        "slowest_branches": list(
            run.slowest_branch_ids
        ),
        "is_slowest_tie": run.is_slowest_tie,
    }


def _parallel_scenario_result_to_dict(
    scenario: ParallelScenarioResult,
) -> dict[str, object]:
    """Convert one parallel scenario result to a report mapping."""
    return {
        "scenario": scenario.scenario_id,
        "duration_unit": scenario.duration_unit,
        "branch_count": {
            "minimum": scenario.branch_count_minimum,
            "maximum": scenario.branch_count_maximum,
            "consistent": (
                scenario.branch_count_consistent
            ),
        },
        "runs": [
            _parallel_run_metrics_to_dict(run)
            for run in scenario.runs
        ],
        "critical_path_duration": (
            _parallel_metric_stats_to_dict(
                scenario.critical_path_duration
            )
        ),
        "spread": _parallel_metric_stats_to_dict(
            scenario.spread
        ),
        "imbalance_ratio": (
            _parallel_metric_stats_to_dict(
                scenario.imbalance_ratio
            )
        ),
    }


def _parallel_analysis_result_to_dict(
    analysis: ParallelAnalysisResult,
) -> dict[str, object]:
    """Convert one parallel analysis result to a report mapping."""
    return {
        "id": analysis.analysis_id,
        "duration_metric": analysis.duration_metric_id,
        "baseline": _parallel_scenario_result_to_dict(
            analysis.baseline
        ),
        "candidate": _parallel_scenario_result_to_dict(
            analysis.candidate
        ),
        "metrics": [
            _metric_comparison_to_dict(metric)
            for metric in analysis.metrics
        ],
    }


def _comparison_summary_row(
    analysis_type: str,
    analysis_id: str,
    baseline_scenario_id: str,
    candidate_scenario_id: str,
    source_metric_id: str,
    metric: MetricComparisonResult,
) -> dict[str, object]:
    """Create one flat comparison summary row."""
    return {
        "analysis_type": analysis_type,
        "analysis_id": analysis_id,
        "baseline_scenario": baseline_scenario_id,
        "candidate_scenario": candidate_scenario_id,
        "source_metric_id": source_metric_id,
        "metric_id": metric.metric_id,
        "unit": metric.unit,
        "baseline_median": metric.baseline_median,
        "candidate_median": metric.candidate_median,
        "absolute_difference": metric.absolute_difference,
        "relative_difference_percent": (
            metric.relative_difference_percent
        ),
    }


def _comparison_summary_rows(
    result: AnalysisResult,
) -> tuple[dict[str, object], ...]:
    """Flatten ordinary and parallel comparisons into CSV rows."""
    rows: list[dict[str, object]] = []

    for comparison in result.comparisons:
        for metric in comparison.metrics:
            rows.append(
                _comparison_summary_row(
                    analysis_type="comparison",
                    analysis_id=comparison.comparison_id,
                    baseline_scenario_id=(
                        comparison.baseline_scenario_id
                    ),
                    candidate_scenario_id=(
                        comparison.candidate_scenario_id
                    ),
                    source_metric_id=metric.metric_id,
                    metric=metric,
                )
            )

    for analysis in result.parallel_analyses:
        for metric in analysis.metrics:
            rows.append(
                _comparison_summary_row(
                    analysis_type="parallel_analysis",
                    analysis_id=analysis.analysis_id,
                    baseline_scenario_id=(
                        analysis.baseline.scenario_id
                    ),
                    candidate_scenario_id=(
                        analysis.candidate.scenario_id
                    ),
                    source_metric_id=(
                        analysis.duration_metric_id
                    ),
                    metric=metric,
                )
            )

    return tuple(rows)


def analysis_result_to_dict(
    result: AnalysisResult,
) -> dict[str, object]:
    """Convert a complete analysis result to a stable report structure."""
    return {
        "version": result.version,
        "experiment": {
            "id": result.experiment.id,
            "title": result.experiment.title,
        },
        "scenarios": [
            _scenario_result_to_dict(scenario)
            for scenario in result.scenarios
        ],
        "comparisons": [
            _comparison_result_to_dict(comparison)
            for comparison in result.comparisons
        ],
        "local_vs_total_impacts": [
            _local_total_impact_to_dict(impact)
            for impact in result.local_total_impacts
        ],
        "bottleneck_candidates": [
            _bottleneck_candidate_to_dict(candidate)
            for candidate in result.bottleneck_candidates
        ],
        "parallel_analyses": [
            _parallel_analysis_result_to_dict(
                analysis
            )
            for analysis in result.parallel_analyses
        ],
    }


def comparison_summary_to_csv(
    result: AnalysisResult,
) -> str:
    """Serialize comparison results as a flat CSV table."""
    stream = StringIO(newline="")

    writer = csv.DictWriter(
        stream,
        fieldnames=_COMPARISON_SUMMARY_COLUMNS,
        lineterminator="\n",
    )

    writer.writeheader()
    writer.writerows(
        _comparison_summary_rows(result)
    )

    return stream.getvalue()


def analysis_result_to_markdown(
    result: AnalysisResult,
) -> str:
    """Serialize a complete analysis as a Markdown report."""
    lines: list[str] = [
        f"# {_escape_markdown_cell(result.experiment.title)}",
        "",
        (
            "Experiment ID: "
            f"`{_escape_markdown_cell(result.experiment.id)}`"
        ),
        "",
        "## Overview",
        "",
        f"- Configuration version: `{result.version}`",
        f"- Scenario results: `{len(result.scenarios)}`",
        f"- Ordinary comparisons: `{len(result.comparisons)}`",
        f"- Parallel analyses: `{len(result.parallel_analyses)}`",
        "",
        "## Scenario statistics",
        "",
    ]

    if not result.scenarios:
        lines.extend(
            [
                "No scenario statistics were produced.",
                "",
            ]
        )
    else:
        for scenario in result.scenarios:
            lines.extend(
                [
                    (
                        "### "
                        f"`{_escape_markdown_cell(scenario.scenario_id)}`"
                    ),
                    "",
                ]
            )

            metric_rows = tuple(
                (
                    _escape_markdown_cell(metric.metric_id),
                    _escape_markdown_cell(metric.unit),
                    _escape_markdown_cell(metric.role),
                    str(metric.count),
                    _format_report_number(metric.median),
                    _format_report_number(metric.mean),
                    _format_report_number(metric.minimum),
                    _format_report_number(metric.maximum),
                    _format_report_number(
                        metric.standard_deviation
                    ),
                )
                for metric in scenario.metrics
            )

            lines.extend(
                _markdown_table(
                    headers=(
                        "Metric",
                        "Unit",
                        "Role",
                        "Count",
                        "Median",
                        "Mean",
                        "Minimum",
                        "Maximum",
                        "Standard deviation",
                    ),
                    rows=metric_rows,
                )
            )
            lines.append("")

    lines.extend(
        [
            "## Comparisons",
            "",
        ]
    )

    if not result.comparisons:
        lines.extend(
            [
                "No ordinary comparisons were configured.",
                "",
            ]
        )
    else:
        for comparison in result.comparisons:
            lines.extend(
                [
                    (
                        "### "
                        f"`{_escape_markdown_cell(comparison.comparison_id)}`"
                    ),
                    "",
                    (
                        "Baseline: "
                        f"`{_escape_markdown_cell(
                            comparison.baseline_scenario_id
                        )}`"
                    ),
                    "",
                    (
                        "Candidate: "
                        f"`{_escape_markdown_cell(
                            comparison.candidate_scenario_id
                        )}`"
                    ),
                    "",
                ]
            )

            comparison_rows = tuple(
                (
                    _escape_markdown_cell(metric.metric_id),
                    _escape_markdown_cell(metric.unit),
                    _format_report_number(
                        metric.baseline_median
                    ),
                    _format_report_number(
                        metric.candidate_median
                    ),
                    _format_report_number(
                        metric.absolute_difference
                    ),
                    _format_report_percent(
                        metric.relative_difference_percent
                    ),
                )
                for metric in comparison.metrics
            )

            lines.extend(
                _markdown_table(
                    headers=(
                        "Metric",
                        "Unit",
                        "Baseline median",
                        "Candidate median",
                        "Absolute difference",
                        "Relative difference",
                    ),
                    rows=comparison_rows,
                )
            )
            lines.append("")

    lines.extend(
        [
            "## Local-versus-total impact",
            "",
        ]
    )

    if not result.local_total_impacts:
        lines.extend(
            [
                (
                    "No local-versus-total impact "
                    "classifications were produced."
                ),
                "",
            ]
        )
    else:
        impact_rows = tuple(
            (
                _escape_markdown_cell(
                    impact.comparison_id
                ),
                _escape_markdown_cell(
                    impact.phase_metric_id
                ),
                _escape_markdown_cell(
                    impact.total_metric_id
                ),
                _format_report_percent(
                    impact.phase_relative_difference_percent
                ),
                _format_report_percent(
                    impact.total_relative_difference_percent
                ),
                _format_report_boolean(
                    impact.substantial_local_improvement
                ),
                _format_report_boolean(
                    impact.limited_total_improvement
                ),
                _format_report_boolean(
                    impact.limited_end_to_end_impact
                ),
            )
            for impact in result.local_total_impacts
        )

        lines.extend(
            _markdown_table(
                headers=(
                    "Comparison",
                    "Phase metric",
                    "Total metric",
                    "Phase change",
                    "Total change",
                    "Substantial local improvement",
                    "Limited total improvement",
                    "Limited end-to-end impact",
                ),
                rows=impact_rows,
            )
        )
        lines.append("")

    lines.extend(
        [
            "## Bottleneck candidates",
            "",
        ]
    )

    if not result.bottleneck_candidates:
        lines.extend(
            [
                "No bottleneck candidates were identified.",
                "",
            ]
        )
    else:
        bottleneck_rows = tuple(
            (
                _escape_markdown_cell(
                    candidate.scenario_id
                ),
                _escape_markdown_cell(
                    ", ".join(
                        candidate.phase_metric_ids
                    )
                ),
                _format_report_number(candidate.median),
                _escape_markdown_cell(candidate.unit),
                _format_report_boolean(
                    candidate.is_tie
                ),
            )
            for candidate in result.bottleneck_candidates
        )

        lines.extend(
            _markdown_table(
                headers=(
                    "Scenario",
                    "Phase metrics",
                    "Median",
                    "Unit",
                    "Tie",
                ),
                rows=bottleneck_rows,
            )
        )
        lines.append("")

    lines.extend(
        [
            "## Parallel-stage analysis",
            "",
        ]
    )

    if not result.parallel_analyses:
        lines.extend(
            [
                "No parallel analyses were configured.",
                "",
            ]
        )
    else:
        for analysis in result.parallel_analyses:
            lines.extend(
                [
                    (
                        "### "
                        f"`{_escape_markdown_cell(analysis.analysis_id)}`"
                    ),
                    "",
                    (
                        "Source duration metric: "
                        f"`{_escape_markdown_cell(
                            analysis.duration_metric_id
                        )}`"
                    ),
                    "",
                ]
            )

            scenario_rows = tuple(
                (
                    scenario_role,
                    _escape_markdown_cell(
                        parallel_scenario.scenario_id
                    ),
                    str(
                        parallel_scenario.branch_count_minimum
                    ),
                    str(
                        parallel_scenario.branch_count_maximum
                    ),
                    _format_report_boolean(
                        parallel_scenario.branch_count_consistent
                    ),
                    _format_report_number(
                        parallel_scenario
                        .critical_path_duration.median
                    ),
                    _format_report_number(
                        parallel_scenario.spread.median
                    ),
                    _format_report_number(
                        parallel_scenario.imbalance_ratio.median
                    ),
                )
                for scenario_role, parallel_scenario in (
                    ("Baseline", analysis.baseline),
                    ("Candidate", analysis.candidate),
                )
            )

            lines.extend(
                _markdown_table(
                    headers=(
                        "Role",
                        "Scenario",
                        "Minimum branches",
                        "Maximum branches",
                        "Consistent",
                        "Critical path median",
                        "Spread median",
                        "Imbalance ratio median",
                    ),
                    rows=scenario_rows,
                )
            )
            lines.append("")

            lines.extend(
                [
                    "#### Comparison metrics",
                    "",
                ]
            )

            parallel_comparison_rows = tuple(
                (
                    _escape_markdown_cell(metric.metric_id),
                    _escape_markdown_cell(metric.unit),
                    _format_report_number(
                        metric.baseline_median
                    ),
                    _format_report_number(
                        metric.candidate_median
                    ),
                    _format_report_number(
                        metric.absolute_difference
                    ),
                    _format_report_percent(
                        metric.relative_difference_percent
                    ),
                )
                for metric in analysis.metrics
            )

            lines.extend(
                _markdown_table(
                    headers=(
                        "Metric",
                        "Unit",
                        "Baseline median",
                        "Candidate median",
                        "Absolute difference",
                        "Relative difference",
                    ),
                    rows=parallel_comparison_rows,
                )
            )
            lines.append("")

            for scenario_role, parallel_scenario in (
                    ("Baseline", analysis.baseline),
                    ("Candidate", analysis.candidate),
            ):
                lines.extend(
                    [
                        (
                            f"#### {scenario_role} runs: "
                            f"`{_escape_markdown_cell(
                                parallel_scenario.scenario_id
                            )}`"
                        ),
                        "",
                    ]
                )

                if not parallel_scenario.runs:
                    lines.extend(
                        [
                            "No run-level results were recorded.",
                            "",
                        ]
                    )
                    continue

                run_rows = tuple(
                    (
                        _escape_markdown_cell(run.run_id),
                        str(run.branch_count),
                        _format_report_number(
                            run.critical_path_duration
                        ),
                        _format_report_number(
                            run.minimum_branch_duration
                        ),
                        _format_report_number(
                            run.mean_branch_duration
                        ),
                        _format_report_number(run.spread),
                        _format_report_number(
                            run.imbalance_ratio
                        ),
                        _escape_markdown_cell(
                            ", ".join(
                                run.slowest_branch_ids
                            )
                        ),
                        _format_report_boolean(
                            run.is_slowest_tie
                        ),
                    )
                    for run in parallel_scenario.runs
                )

                lines.extend(
                    _markdown_table(
                        headers=(
                            "Run",
                            "Branches",
                            "Critical path",
                            "Minimum branch",
                            "Mean branch",
                            "Spread",
                            "Imbalance ratio",
                            "Slowest branches",
                            "Tie",
                        ),
                        rows=run_rows,
                    )
                )
                lines.append("")

    lines.extend(
        [
            "## Warnings",
            "",
        ]
    )

    warnings = _analysis_warnings(result)

    if warnings:
        lines.extend(
            f"- {_escape_markdown_cell(warning)}"
            for warning in warnings
        )
        lines.append("")
    else:
        lines.extend(
            [
                "No warnings.",
                "",
            ]
        )

    lines.extend(
        [
            "## Limitations",
            "",
            "- Comparisons use scenario medians.",
            (
                "- Bottleneck candidates are based only on "
                "configured measured phase durations."
            ),
            (
                "- Parallel critical-path duration covers only "
                "the configured parallel stage."
            ),
            (
                "- The report does not reconstruct the dependency "
                "graph of the complete CI pipeline."
            ),
        ]
    )

    return "\n".join(lines).rstrip() + "\n"


def write_analysis_report(
    result: AnalysisResult,
    output_directory: str | Path,
) -> Path:
    """Write the complete experiment analysis as JSON."""
    destination = Path(output_directory)
    destination.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path = destination / "analysis.json"

    report_content = json.dumps(
        analysis_result_to_dict(result),
        indent=2,
        ensure_ascii=False,
    )

    report_path.write_text(
        report_content + "\n",
        encoding="utf-8",
        newline="",
    )

    return report_path


def write_analysis_reports(
    result: AnalysisResult,
    output_directory: str | Path,
) -> AnalysisReportPaths:
    """Write JSON, CSV, and Markdown experiment reports."""
    destination = Path(output_directory)
    destination.mkdir(
        parents=True,
        exist_ok=True,
    )

    analysis_json_path = write_analysis_report(
        result,
        destination,
    )
    summary_csv_path = destination / "summary.csv"
    report_markdown_path = destination / "report.md"

    summary_csv_path.write_text(
        comparison_summary_to_csv(result),
        encoding="utf-8",
        newline="",
    )

    report_markdown_path.write_text(
        analysis_result_to_markdown(result),
        encoding="utf-8",
        newline="",
    )

    return AnalysisReportPaths(
        analysis_json=analysis_json_path,
        summary_csv=summary_csv_path,
        report_markdown=report_markdown_path,
    )