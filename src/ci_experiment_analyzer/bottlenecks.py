"""Identify bottleneck candidates from measured scenario phases."""

import math
from collections.abc import Mapping

from ci_experiment_analyzer.models import (
    BottleneckCandidateResult,
    MetricConfig,
    MetricStats,
    ScenarioResult,
)


def _is_duration_phase(
    metric: MetricStats,
    metrics: Mapping[str, MetricConfig],
) -> bool:
    """Return whether a result represents a measured duration phase."""
    metric_config = metrics[metric.metric_id]

    return (
        metric_config.metric_type == "duration"
        and metric_config.role == "phase"
    )


def identify_bottleneck_candidate(
    scenario: ScenarioResult,
    metrics: Mapping[str, MetricConfig],
) -> BottleneckCandidateResult | None:
    """Identify the longest measured duration phase in one scenario."""
    phase_metrics = tuple(
        metric
        for metric in scenario.metrics
        if _is_duration_phase(
            metric=metric,
            metrics=metrics,
        )
    )

    if not phase_metrics:
        return None

    longest_median = max(
        metric.median
        for metric in phase_metrics
    )

    candidate_metrics = tuple(
        metric
        for metric in phase_metrics
        if math.isclose(
            metric.median,
            longest_median,
            rel_tol=1e-9,
            abs_tol=1e-9,
        )
    )

    return BottleneckCandidateResult(
        scenario_id=scenario.scenario_id,
        phase_metric_ids=tuple(
            metric.metric_id
            for metric in candidate_metrics
        ),
        median=longest_median,
        unit=candidate_metrics[0].unit,
        is_tie=len(candidate_metrics) > 1,
    )