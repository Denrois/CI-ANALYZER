"""Compare baseline and candidate CI experiment scenarios."""

from collections.abc import Mapping

from ci_experiment_analyzer.models import (
    ComparisonConfig,
    ComparisonResult,
    MetricComparisonResult,
    MetricConfig,
    ScenarioDataset,
)
from ci_experiment_analyzer.normalization import normalized_metric_unit
from ci_experiment_analyzer.statistics import calculate_median


def calculate_relative_difference_percent(
    baseline: float,
    candidate: float,
) -> float | None:
    """Calculate signed relative difference from baseline in percent."""
    if baseline == 0:
        return None

    return ((candidate - baseline) / baseline) * 100.0


def _metric_values(
    dataset: ScenarioDataset,
    metric_id: str,
) -> tuple[float, ...]:
    """Extract all values of one metric from a scenario dataset."""
    return tuple(
        record.metric_values[metric_id]
        for record in dataset.records
    )


def compare_metric(
    metric: MetricConfig,
    baseline_dataset: ScenarioDataset,
    candidate_dataset: ScenarioDataset,
) -> MetricComparisonResult:
    """Compare median values of one metric."""
    baseline_median = calculate_median(
        _metric_values(baseline_dataset, metric.id)
    )
    candidate_median = calculate_median(
        _metric_values(candidate_dataset, metric.id)
    )

    return MetricComparisonResult(
        metric_id=metric.id,
        unit=normalized_metric_unit(metric),
        baseline_median=baseline_median,
        candidate_median=candidate_median,
        absolute_difference=candidate_median - baseline_median,
        relative_difference_percent=calculate_relative_difference_percent(
            baseline=baseline_median,
            candidate=candidate_median,
        ),
    )


def compare_scenarios(
    comparison: ComparisonConfig,
    datasets: Mapping[str, ScenarioDataset],
    metrics: Mapping[str, MetricConfig],
) -> ComparisonResult:
    """Compare configured metrics between baseline and candidate scenarios."""
    baseline_dataset = datasets[comparison.baseline]
    candidate_dataset = datasets[comparison.candidate]

    metric_results = tuple(
        compare_metric(
            metric=metrics[metric_id],
            baseline_dataset=baseline_dataset,
            candidate_dataset=candidate_dataset,
        )
        for metric_id in comparison.metrics
    )

    return ComparisonResult(
        comparison_id=comparison.id,
        baseline_scenario_id=comparison.baseline,
        candidate_scenario_id=comparison.candidate,
        metrics=metric_results,
    )