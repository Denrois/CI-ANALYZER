"""Statistical calculations for CI experiment metrics."""

from collections.abc import Sequence
from statistics import mean, median, stdev

from ci_experiment_analyzer.models import (
    MetricConfig,
    MetricStats,
    ScenarioDataset,
    ScenarioResult,
)
from ci_experiment_analyzer.normalization import normalized_metric_unit


def _require_values(
    values: Sequence[float],
    metric_id: str,
) -> None:
    """Reject an empty metric value sequence."""
    if not values:
        raise ValueError(
            f"Cannot calculate statistics for metric "
            f"{metric_id!r} from an empty sequence."
        )


def calculate_median(values: Sequence[float]) -> float:
    """Calculate the median of a non-empty numeric sequence."""
    if not values:
        raise ValueError(
            "Cannot calculate median for an empty sequence."
        )

    return float(median(values))


def calculate_standard_deviation(
    values: Sequence[float],
) -> float:
    """Calculate sample standard deviation.

    A single observation has a standard deviation of zero because
    sample standard deviation requires at least two observations.
    """
    if not values:
        raise ValueError(
            "Cannot calculate standard deviation "
            "for an empty sequence."
        )

    if len(values) == 1:
        return 0.0

    return float(stdev(values))


def calculate_metric_stats(
    metric: MetricConfig,
    values: Sequence[float],
) -> MetricStats:
    """Calculate descriptive statistics for one configured metric."""
    _require_values(
        values=values,
        metric_id=metric.id,
    )

    return MetricStats(
        metric_id=metric.id,
        unit=normalized_metric_unit(metric),
        role=metric.role,
        count=len(values),
        median=calculate_median(values),
        mean=float(mean(values)),
        minimum=float(min(values)),
        maximum=float(max(values)),
        standard_deviation=calculate_standard_deviation(values),
    )


def _metric_values(
    dataset: ScenarioDataset,
    metric_id: str,
) -> tuple[float, ...]:
    """Extract values of one metric from a scenario dataset."""
    return tuple(
        record.metric_values[metric_id]
        for record in dataset.records
    )


def calculate_scenario_result(
    dataset: ScenarioDataset,
    metrics: Sequence[MetricConfig],
) -> ScenarioResult:
    """Calculate statistics for every configured scenario metric."""
    metric_results = tuple(
        calculate_metric_stats(
            metric=metric,
            values=_metric_values(
                dataset=dataset,
                metric_id=metric.id,
            ),
        )
        for metric in metrics
    )

    return ScenarioResult(
        scenario_id=dataset.scenario_id,
        metrics=metric_results,
    )