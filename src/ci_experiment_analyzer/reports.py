"""Generate CI experiment reports."""

import csv
import json
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
    )

    return report_path