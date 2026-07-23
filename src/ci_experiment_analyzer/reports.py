"""Generate machine-readable CI experiment reports."""

import json
from pathlib import Path

from ci_experiment_analyzer.models import (
    AnalysisResult,
    ComparisonResult,
    LocalTotalImpactResult,
    MetricComparisonResult,
    MetricStats,
    ScenarioResult,
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
    }


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
    }


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