"""Tests for metric value normalization."""

import pytest

from ci_experiment_analyzer.models import MetricConfig
from ci_experiment_analyzer.normalization import (
    normalize_metric_value,
    normalized_metric_unit,
)


@pytest.mark.parametrize(
    ("source_unit", "source_value", "expected_value"),
    [
        ("milliseconds", 1_500.0, 1_500.0),
        ("seconds", 1.5, 1_500.0),
        ("minutes", 1.5, 90_000.0),
    ],
)
def test_duration_values_are_normalized_to_milliseconds(
    source_unit: str,
    source_value: float,
    expected_value: float,
) -> None:
    """Every supported duration unit should become milliseconds."""
    metric = MetricConfig(
        id="duration",
        field="duration",
        metric_type="duration",
        unit=source_unit,
        role="total",
    )

    result = normalize_metric_value(
        metric=metric,
        value=source_value,
    )

    assert result == pytest.approx(expected_value)
    assert normalized_metric_unit(metric) == "milliseconds"


def test_number_metric_is_not_converted() -> None:
    """Non-duration numeric metrics should preserve their values."""
    metric = MetricConfig(
        id="test_count",
        field="test_count",
        metric_type="number",
        unit="count",
        role="total",
    )

    result = normalize_metric_value(
        metric=metric,
        value=42.0,
    )

    assert result == 42.0
    assert normalized_metric_unit(metric) == "count"