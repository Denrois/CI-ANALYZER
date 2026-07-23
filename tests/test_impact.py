"""Tests for local-versus-total impact calculations."""

from ci_experiment_analyzer.impact import (
    calculate_local_total_impacts,
)
from ci_experiment_analyzer.models import (
    ComparisonResult,
    LocalTotalImpactResult,
    MetricComparisonResult,
    MetricConfig,
)


def _duration_metric(
    metric_id: str,
    role: str,
) -> MetricConfig:
    """Create a configured duration metric."""
    return MetricConfig(
        id=metric_id,
        field=f"{metric_id}_seconds",
        metric_type="duration",
        unit="seconds",
        role=role,
    )


def _comparison_metric(
    metric_id: str,
    relative_difference_percent: float | None,
) -> MetricComparisonResult:
    """Create one comparison metric result."""
    return MetricComparisonResult(
        metric_id=metric_id,
        unit="milliseconds",
        baseline_median=100_000.0,
        candidate_median=90_000.0,
        absolute_difference=-10_000.0,
        relative_difference_percent=relative_difference_percent,
    )


def test_calculate_local_total_impact() -> None:
    """A phase duration should be paired with a total duration."""
    comparison = ComparisonResult(
        comparison_id="optimization-impact",
        baseline_scenario_id="baseline",
        candidate_scenario_id="optimized",
        metrics=(
            _comparison_metric(
                metric_id="phase_duration",
                relative_difference_percent=-16.1,
            ),
            _comparison_metric(
                metric_id="total_duration",
                relative_difference_percent=-3.9,
            ),
        ),
    )

    metrics = {
        "phase_duration": _duration_metric(
            metric_id="phase_duration",
            role="phase",
        ),
        "total_duration": _duration_metric(
            metric_id="total_duration",
            role="total",
        ),
    }

    result = calculate_local_total_impacts(
        comparison=comparison,
        metrics=metrics,
    )

    assert result == (
        LocalTotalImpactResult(
            comparison_id="optimization-impact",
            phase_metric_id="phase_duration",
            total_metric_id="total_duration",
            phase_relative_difference_percent=-16.1,
            total_relative_difference_percent=-3.9,
        ),
    )


def test_calculate_impact_for_multiple_phase_metrics() -> None:
    """Every phase metric should be compared with the total metric."""
    comparison = ComparisonResult(
        comparison_id="multi-phase-impact",
        baseline_scenario_id="baseline",
        candidate_scenario_id="optimized",
        metrics=(
            _comparison_metric(
                metric_id="install_duration",
                relative_difference_percent=-20.0,
            ),
            _comparison_metric(
                metric_id="build_duration",
                relative_difference_percent=-10.0,
            ),
            _comparison_metric(
                metric_id="total_duration",
                relative_difference_percent=-4.0,
            ),
        ),
    )

    metrics = {
        "install_duration": _duration_metric(
            metric_id="install_duration",
            role="phase",
        ),
        "build_duration": _duration_metric(
            metric_id="build_duration",
            role="phase",
        ),
        "total_duration": _duration_metric(
            metric_id="total_duration",
            role="total",
        ),
    }

    result = calculate_local_total_impacts(
        comparison=comparison,
        metrics=metrics,
    )

    assert tuple(
        impact.phase_metric_id
        for impact in result
    ) == (
        "install_duration",
        "build_duration",
    )

    assert all(
        impact.total_metric_id == "total_duration"
        for impact in result
    )


def test_impact_requires_phase_and_total_duration_metrics() -> None:
    """A comparison without both duration roles has no impact result."""
    comparison = ComparisonResult(
        comparison_id="number-only",
        baseline_scenario_id="baseline",
        candidate_scenario_id="optimized",
        metrics=(
            _comparison_metric(
                metric_id="score",
                relative_difference_percent=-20.0,
            ),
        ),
    )

    metrics = {
        "score": MetricConfig(
            id="score",
            field="score",
            metric_type="number",
            unit="points",
            role="phase",
        ),
    }

    result = calculate_local_total_impacts(
        comparison=comparison,
        metrics=metrics,
    )

    assert result == ()