"""Statistical calculations for CI experiment metrics."""

from collections.abc import Sequence
from statistics import median


def calculate_median(values: Sequence[float]) -> float:
    """Calculate the median of a non-empty numeric sequence."""
    if not values:
        raise ValueError("Cannot calculate median for an empty sequence.")

    return float(median(values))