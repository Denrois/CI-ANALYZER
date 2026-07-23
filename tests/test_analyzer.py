"""Tests for experiment analysis orchestration."""

from pathlib import Path

import pytest

from ci_experiment_analyzer.analyzer import analyze_experiment
from ci_experiment_analyzer.models import (
    ComparisonConfig,
    ExperimentConfig,
    ExperimentMetadata,
    MetricConfig,
    ScenarioConfig,
    SourceConfig,
)


def test_analyze_experiment_builds_complete_result(
    tmp_path: Path,
) -> None:
    """Analysis should contain scenario statistics and comparisons."""
    baseline_path = tmp_path / "baseline.csv"
    baseline_path.write_text(
        (
            "run_id,total_seconds\n"
            "baseline-1,10.0\n"
            "baseline-2,14.0\n"
        ),
        encoding="utf-8",
    )

    optimized_path = tmp_path / "optimized.csv"
    optimized_path.write_text(
        (
            "run_id,total_seconds\n"
            "optimized-1,8.0\n"
            "optimized-2,10.0\n"
        ),
        encoding="utf-8",
    )

    config = ExperimentConfig(
        version=1,
        experiment=ExperimentMetadata(
            id="analysis-example",
            title="Analysis example",
        ),
        scenarios=(
            ScenarioConfig(
                id="baseline",
                source=SourceConfig(
                    format="csv",
                    path=baseline_path,
                ),
            ),
            ScenarioConfig(
                id="optimized",
                source=SourceConfig(
                    format="csv",
                    path=optimized_path,
                ),
            ),
        ),
        record_mapping={
            "run_id": "run_id",
        },
        metrics=(
            MetricConfig(
                id="total_duration",
                field="total_seconds",
                metric_type="duration",
                unit="seconds",
                role="total",
            ),
        ),
        comparisons=(
            ComparisonConfig(
                id="optimization-impact",
                baseline="baseline",
                candidate="optimized",
                metrics=("total_duration",),
            ),
        ),
    )

    result = analyze_experiment(config)

    assert result.version == 1
    assert result.experiment.id == "analysis-example"
    assert len(result.scenarios) == 2
    assert len(result.comparisons) == 1

    baseline_stats = result.scenarios[0].metrics[0]

    assert baseline_stats.metric_id == "total_duration"
    assert baseline_stats.count == 2
    assert baseline_stats.median == 12_000.0
    assert baseline_stats.mean == 12_000.0
    assert baseline_stats.minimum == 10_000.0
    assert baseline_stats.maximum == 14_000.0
    assert baseline_stats.standard_deviation == pytest.approx(
        2_828.42712474619
    )

    optimized_stats = result.scenarios[1].metrics[0]

    assert optimized_stats.median == 9_000.0

    comparison = result.comparisons[0]
    comparison_metric = comparison.metrics[0]

    assert comparison.comparison_id == "optimization-impact"
    assert comparison.baseline_scenario_id == "baseline"
    assert comparison.candidate_scenario_id == "optimized"
    assert comparison_metric.baseline_median == 12_000.0
    assert comparison_metric.candidate_median == 9_000.0
    assert comparison_metric.absolute_difference == -3_000.0
    assert comparison_metric.relative_difference_percent == -25.0