"""Generate analysis reports."""

import json
from collections.abc import Sequence
from pathlib import Path

from ci_experiment_analyzer.models import (
    ComparisonResult,
    ExperimentConfig,
    MetricComparisonResult,
)


def _serialize_metric_result(
    result: MetricComparisonResult,
) -> dict[str, object]:
    """Convert one metric comparison result to JSON-compatible data."""
    return {
        "id": result.metric_id,
        "unit": result.unit,
        "baseline_median": result.baseline_median,
        "candidate_median": result.candidate_median,
        "absolute_difference": result.absolute_difference,
        "relative_difference_percent": result.relative_difference_percent,
    }


def _serialize_comparison_result(
    result: ComparisonResult,
) -> dict[str, object]:
    """Convert one scenario comparison result to JSON-compatible data."""
    return {
        "id": result.comparison_id,
        "baseline": result.baseline_scenario_id,
        "candidate": result.candidate_scenario_id,
        "metrics": [
            _serialize_metric_result(metric_result)
            for metric_result in result.metrics
        ],
    }


def build_analysis_document(
    config: ExperimentConfig,
    comparison_results: Sequence[ComparisonResult],
) -> dict[str, object]:
    """Build the complete JSON-compatible analysis document."""
    return {
        "version": config.version,
        "experiment": {
            "id": config.experiment.id,
            "title": config.experiment.title,
        },
        "comparisons": [
            _serialize_comparison_result(result)
            for result in comparison_results
        ],
    }


def write_analysis_json(
    config: ExperimentConfig,
    comparison_results: Sequence[ComparisonResult],
    output_directory: Path,
) -> Path:
    """Write the analysis result to analysis.json."""
    output_directory.mkdir(parents=True, exist_ok=True)

    report_path = output_directory / "analysis.json"
    document = build_analysis_document(
        config=config,
        comparison_results=comparison_results,
    )

    report_path.write_text(
        json.dumps(
            document,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return report_path