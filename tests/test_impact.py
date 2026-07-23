"""Tests for local-versus-total impact calculations."""

from ci_experiment_analyzer.impact import (
    calculate_local_total_impacts,
)
from ci_experiment_analyzer.models import (
    AnalysisConfig,
    ComparisonResult,
    LocalTotalImpactResult,
    MetricComparisonResult,
    MetricConfig,
)

EXPECTED_WARNING = (
    "The local phase improved substantially, but the total pipeline "
    "improvement remained below the configured threshold."
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


def _comparison(
    phase_difference: float | None,
    total_difference: float | None,
) -> ComparisonResult:
    """Create a phase-and-total comparison."""
    return ComparisonResult(
        comparison_id="optimization-impact",
        baseline_scenario_id="baseline",
        candidate_scenario_id="optimized",
        metrics=(
            _comparison_metric(
                metric_id="phase_duration",
                relative_difference_percent=phase_difference,
            ),
            _comparison_metric(
                metric_id="total_duration",
                relative_difference_percent=total_difference,
            ),
        ),
    )


def _metrics() -> dict[str, MetricConfig]:
    """Create phase and total duration metric definitions."""
    return {
        "phase_duration": _duration_metric(
            metric_id="phase_duration",
            role="phase",
        ),
        "total_duration": _duration_metric(
            metric_id="total_duration",
            role="total",
        ),
    }


def test_detects_limited_end_to_end_impact() -> None:
    """Strong local improvement with weak total impact should warn."""
    result = calculate_local_total_impacts(
        comparison=_comparison(
            phase_difference=-16.1,
            total_difference=-3.9,
        ),
        metrics=_metrics(),
        analysis=AnalysisConfig(
            local_improvement_threshold_pct=10.0,
            total_impact_threshold_pct=5.0,
        ),
    )

    assert result == (
        LocalTotalImpactResult(
            comparison_id="optimization-impact",
            phase_metric_id="phase_duration",
            total_metric_id="total_duration",
            phase_relative_difference_percent=-16.1,
            total_relative_difference_percent=-3.9,
            local_improvement_threshold_pct=10.0,
            total_impact_threshold_pct=5.0,
            substantial_local_improvement=True,
            limited_total_improvement=True,
            limited_end_to_end_impact=True,
            warning=EXPECTED_WARNING,
        ),
    )


def test_does_not_warn_when_total_improvement_reaches_threshold() -> None:
    """Meaningful total improvement should not produce a warning."""
    result = calculate_local_total_impacts(
        comparison=_comparison(
            phase_difference=-16.1,
            total_difference=-5.0,
        ),
        metrics=_metrics(),
        analysis=AnalysisConfig(
            local_improvement_threshold_pct=10.0,
            total_impact_threshold_pct=5.0,
        ),
    )

    impact = result[0]

    assert impact.substantial_local_improvement is True
    assert impact.limited_total_improvement is False
    assert impact.limited_end_to_end_impact is False
    assert impact.warning is None


def test_does_not_warn_without_substantial_local_improvement() -> None:
    """Weak local improvement should not trigger the warning."""
    result = calculate_local_total_impacts(
        comparison=_comparison(
            phase_difference=-8.0,
            total_difference=-3.0,
        ),
        metrics=_metrics(),
        analysis=AnalysisConfig(
            local_improvement_threshold_pct=10.0,
            total_impact_threshold_pct=5.0,
        ),
    )

    impact = result[0]

    assert impact.substantial_local_improvement is False
    assert impact.limited_total_improvement is True
    assert impact.limited_end_to_end_impact is False
    assert impact.warning is None


def test_unavailable_relative_change_is_not_classified() -> None:
    """A zero baseline should produce an incomplete classification."""
    result = calculate_local_total_impacts(
        comparison=_comparison(
            phase_difference=None,
            total_difference=-3.0,
        ),
        metrics=_metrics(),
        analysis=AnalysisConfig(),
    )

    impact = result[0]

    assert impact.substantial_local_improvement is None
    assert impact.limited_total_improvement is True
    assert impact.limited_end_to_end_impact is None
    assert impact.warning is None


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
        analysis=AnalysisConfig(),
    )

    assert result == ()