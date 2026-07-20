"""Normalize experiment metric values."""

from ci_experiment_analyzer.models import MetricConfig

_DURATION_FACTORS_TO_MILLISECONDS = {
    "milliseconds": 1.0,
    "seconds": 1_000.0,
    "minutes": 60_000.0,
}


def normalize_metric_value(
    metric: MetricConfig,
    value: float,
) -> float:
    """Convert a metric value to its internal normalized unit."""
    if metric.metric_type != "duration":
        return value

    return value * _DURATION_FACTORS_TO_MILLISECONDS[metric.unit]


def normalized_metric_unit(metric: MetricConfig) -> str:
    """Return the unit used for a normalized metric."""
    if metric.metric_type == "duration":
        return "milliseconds"

    return metric.unit