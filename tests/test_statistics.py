"""Tests for statistical calculations."""

import pytest

from ci_experiment_analyzer.comparisons import (
    calculate_relative_difference_percent,
)
from ci_experiment_analyzer.statistics import calculate_median


def test_calculate_median_for_odd_and_even_sequences() -> None:
    """Median should work for both odd and even record counts."""
    assert calculate_median([1.0, 3.0, 2.0]) == 2.0
    assert calculate_median([1.0, 2.0, 3.0, 4.0]) == 2.5


def test_calculate_median_rejects_empty_sequence() -> None:
    """An empty sequence should not produce a misleading result."""
    with pytest.raises(
        ValueError,
        match="Cannot calculate median for an empty sequence",
    ):
        calculate_median([])


def test_calculate_relative_difference_percent() -> None:
    """Relative difference should use baseline as the denominator."""
    result = calculate_relative_difference_percent(
        baseline=100.0,
        candidate=80.0,
    )

    assert result == pytest.approx(-20.0)


def test_relative_difference_is_undefined_for_zero_baseline() -> None:
    """Relative difference cannot be calculated from a zero baseline."""
    result = calculate_relative_difference_percent(
        baseline=0.0,
        candidate=10.0,
    )

    assert result is None