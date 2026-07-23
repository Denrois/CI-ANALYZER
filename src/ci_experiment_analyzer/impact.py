"""Analyze local phase changes relative to total scenario changes."""

from collections.abc import Mapping

from ci_experiment_analyzer.models import (
    ComparisonResult,
    LocalTotalImpactResult,
    MetricConfig,
)


def calculate_local_total_impacts(
    comparison: ComparisonResult,
    metrics: Mapping[str, MetricConfig],
) -> tuple[LocalTotalImpactResult, ...]:
    """Pair duration phase metrics with duration total metrics.

    Only metrics participating in the provided comparison are considered.
    Generic numeric metrics are excluded because local-versus-total impact
    currently describes CI duration changes.
    """
    phase_results = tuple(
        metric_result
        for metric_result in comparison.metrics
        if (
            metrics[metric_result.metric_id].metric_type == "duration"
            and metrics[metric_result.metric_id].role == "phase"
        )
    )

    total_results = tuple(
        metric_result
        for metric_result in comparison.metrics
        if (
            metrics[metric_result.metric_id].metric_type == "duration"
            and metrics[metric_result.metric_id].role == "total"
        )
    )

    return tuple(
        LocalTotalImpactResult(
            comparison_id=comparison.comparison_id,
            phase_metric_id=phase_result.metric_id,
            total_metric_id=total_result.metric_id,
            phase_relative_difference_percent=(
                phase_result.relative_difference_percent
            ),
            total_relative_difference_percent=(
                total_result.relative_difference_percent
            ),
        )
        for phase_result in phase_results
        for total_result in total_results
    )