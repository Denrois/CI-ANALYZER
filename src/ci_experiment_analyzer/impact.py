"""Analyze local phase changes relative to total scenario changes."""

from collections.abc import Mapping

from ci_experiment_analyzer.models import (
    AnalysisConfig,
    ComparisonResult,
    LocalTotalImpactResult,
    MetricConfig,
)

LIMITED_END_TO_END_IMPACT_WARNING = (
    "The local phase improved substantially, but the total pipeline "
    "improvement remained below the configured threshold."
)


def _classify_local_total_impact(
    phase_relative_difference_percent: float | None,
    total_relative_difference_percent: float | None,
    analysis: AnalysisConfig,
) -> tuple[
    bool | None,
    bool | None,
    bool | None,
    str | None,
]:
    """Classify local and total improvement using configured thresholds."""
    if phase_relative_difference_percent is None:
        substantial_local_improvement = None
    else:
        substantial_local_improvement = (
            phase_relative_difference_percent < 0.0
            and -phase_relative_difference_percent
            >= analysis.local_improvement_threshold_pct
        )

    if total_relative_difference_percent is None:
        limited_total_improvement = None
    else:
        meaningful_total_improvement = (
            total_relative_difference_percent < 0.0
            and -total_relative_difference_percent
            >= analysis.total_impact_threshold_pct
        )

        limited_total_improvement = not meaningful_total_improvement

    if (
        substantial_local_improvement is None
        or limited_total_improvement is None
    ):
        limited_end_to_end_impact = None
    else:
        limited_end_to_end_impact = (
            substantial_local_improvement
            and limited_total_improvement
        )

    warning = (
        LIMITED_END_TO_END_IMPACT_WARNING
        if limited_end_to_end_impact is True
        else None
    )

    return (
        substantial_local_improvement,
        limited_total_improvement,
        limited_end_to_end_impact,
        warning,
    )


def calculate_local_total_impacts(
    comparison: ComparisonResult,
    metrics: Mapping[str, MetricConfig],
    analysis: AnalysisConfig,
) -> tuple[LocalTotalImpactResult, ...]:
    """Pair duration phase metrics with duration total metrics."""
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

    results: list[LocalTotalImpactResult] = []

    for phase_result in phase_results:
        for total_result in total_results:
            (
                substantial_local_improvement,
                limited_total_improvement,
                limited_end_to_end_impact,
                warning,
            ) = _classify_local_total_impact(
                phase_relative_difference_percent=(
                    phase_result.relative_difference_percent
                ),
                total_relative_difference_percent=(
                    total_result.relative_difference_percent
                ),
                analysis=analysis,
            )

            results.append(
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
                    local_improvement_threshold_pct=(
                        analysis.local_improvement_threshold_pct
                    ),
                    total_impact_threshold_pct=(
                        analysis.total_impact_threshold_pct
                    ),
                    substantial_local_improvement=(
                        substantial_local_improvement
                    ),
                    limited_total_improvement=(
                        limited_total_improvement
                    ),
                    limited_end_to_end_impact=(
                        limited_end_to_end_impact
                    ),
                    warning=warning,
                )
            )

    return tuple(results)