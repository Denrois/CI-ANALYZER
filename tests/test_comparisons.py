"""Tests for scenario comparisons."""

import pytest

from ci_experiment_analyzer.comparisons import compare_scenarios
from ci_experiment_analyzer.models import (
    ComparisonConfig,
    MetricConfig,
    RunRecord,
    ScenarioDataset,
)


def test_compare_scenario_medians() -> None:
    """Configured scenario metrics should be compared by median."""
    datasets = {
        "baseline": ScenarioDataset(
            scenario_id="baseline",
            records=(
                RunRecord(
                    run_id="baseline-1",
                    metric_values={"duration": 10_000.0},
                ),
                RunRecord(
                    run_id="baseline-2",
                    metric_values={"duration": 14_000.0},
                ),
            ),
        ),
        "optimized": ScenarioDataset(
            scenario_id="optimized",
            records=(
                RunRecord(
                    run_id="optimized-1",
                    metric_values={"duration": 8_000.0},
                ),
                RunRecord(
                    run_id="optimized-2",
                    metric_values={"duration": 10_000.0},
                ),
            ),
        ),
    }

    metrics = {
        "duration": MetricConfig(
            id="duration",
            field="duration",
            metric_type="duration",
            unit="seconds",
            role="total",
        )
    }

    comparison = ComparisonConfig(
        id="duration-impact",
        baseline="baseline",
        candidate="optimized",
        metrics=("duration",),
    )

    result = compare_scenarios(
        comparison=comparison,
        datasets=datasets,
        metrics=metrics,
    )

    assert result.comparison_id == "duration-impact"
    assert result.baseline_scenario_id == "baseline"
    assert result.candidate_scenario_id == "optimized"

    assert len(result.metrics) == 1

    metric_result = result.metrics[0]

    assert metric_result.metric_id == "duration"
    assert metric_result.unit == "milliseconds"
    assert metric_result.baseline_median == pytest.approx(12_000.0)
    assert metric_result.candidate_median == pytest.approx(9_000.0)
    assert metric_result.absolute_difference == pytest.approx(-3_000.0)
    assert metric_result.relative_difference_percent == pytest.approx(-25.0)