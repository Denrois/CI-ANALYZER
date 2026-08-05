"""Tests for measured phase bottleneck detection."""

from ci_experiment_analyzer.bottlenecks import (
    identify_bottleneck_candidate,
)
from ci_experiment_analyzer.models import (
    BottleneckCandidateResult,
    MetricConfig,
    MetricStats,
    ScenarioResult,
)


def _metric_config(
    metric_id: str,
    metric_type: str,
    unit: str,
    role: str,
) -> MetricConfig:
    """Create one metric configuration."""
    return MetricConfig(
        id=metric_id,
        field=metric_id,
        metric_type=metric_type,
        unit=unit,
        role=role,
    )


def _metric_stats(
    metric_id: str,
    unit: str,
    role: str,
    median: float,
) -> MetricStats:
    """Create deterministic metric statistics."""
    return MetricStats(
        metric_id=metric_id,
        unit=unit,
        role=role,
        count=3,
        median=median,
        mean=median,
        minimum=median,
        maximum=median,
        standard_deviation=0.0,
    )


def test_identifies_longest_measured_duration_phase() -> None:
    """The phase with the largest median should be the candidate."""
    scenario = ScenarioResult(
        scenario_id="baseline",
        metrics=(
            _metric_stats(
                metric_id="install_duration",
                unit="milliseconds",
                role="phase",
                median=12_000.0,
            ),
            _metric_stats(
                metric_id="build_duration",
                unit="milliseconds",
                role="phase",
                median=20_000.0,
            ),
            _metric_stats(
                metric_id="total_duration",
                unit="milliseconds",
                role="total",
                median=54_000.0,
            ),
        ),
    )

    metrics = {
        "install_duration": _metric_config(
            metric_id="install_duration",
            metric_type="duration",
            unit="seconds",
            role="phase",
        ),
        "build_duration": _metric_config(
            metric_id="build_duration",
            metric_type="duration",
            unit="seconds",
            role="phase",
        ),
        "total_duration": _metric_config(
            metric_id="total_duration",
            metric_type="duration",
            unit="seconds",
            role="total",
        ),
    }

    result = identify_bottleneck_candidate(
        scenario=scenario,
        metrics=metrics,
    )

    assert result == BottleneckCandidateResult(
        scenario_id="baseline",
        phase_metric_ids=("build_duration",),
        median=20_000.0,
        unit="milliseconds",
        is_tie=False,
    )


def test_excludes_total_and_generic_number_metrics() -> None:
    """Only duration metrics with the phase role should participate."""
    scenario = ScenarioResult(
        scenario_id="baseline",
        metrics=(
            _metric_stats(
                metric_id="total_duration",
                unit="milliseconds",
                role="total",
                median=60_000.0,
            ),
            _metric_stats(
                metric_id="quality_score",
                unit="points",
                role="phase",
                median=100_000.0,
            ),
        ),
    )

    metrics = {
        "total_duration": _metric_config(
            metric_id="total_duration",
            metric_type="duration",
            unit="seconds",
            role="total",
        ),
        "quality_score": _metric_config(
            metric_id="quality_score",
            metric_type="number",
            unit="points",
            role="phase",
        ),
    }

    result = identify_bottleneck_candidate(
        scenario=scenario,
        metrics=metrics,
    )

    assert result is None


def test_reports_all_tied_longest_phases_in_stable_order() -> None:
    """All equally long phases should be returned in scenario order."""
    scenario = ScenarioResult(
        scenario_id="baseline",
        metrics=(
            _metric_stats(
                metric_id="install_duration",
                unit="milliseconds",
                role="phase",
                median=20_000.0,
            ),
            _metric_stats(
                metric_id="build_duration",
                unit="milliseconds",
                role="phase",
                median=20_000.0,
            ),
            _metric_stats(
                metric_id="test_duration",
                unit="milliseconds",
                role="phase",
                median=15_000.0,
            ),
            _metric_stats(
                metric_id="total_duration",
                unit="milliseconds",
                role="total",
                median=70_000.0,
            ),
        ),
    )

    metrics = {
        "install_duration": _metric_config(
            metric_id="install_duration",
            metric_type="duration",
            unit="seconds",
            role="phase",
        ),
        "build_duration": _metric_config(
            metric_id="build_duration",
            metric_type="duration",
            unit="seconds",
            role="phase",
        ),
        "test_duration": _metric_config(
            metric_id="test_duration",
            metric_type="duration",
            unit="seconds",
            role="phase",
        ),
        "total_duration": _metric_config(
            metric_id="total_duration",
            metric_type="duration",
            unit="seconds",
            role="total",
        ),
    }

    result = identify_bottleneck_candidate(
        scenario=scenario,
        metrics=metrics,
    )

    assert result == BottleneckCandidateResult(
        scenario_id="baseline",
        phase_metric_ids=(
            "install_duration",
            "build_duration",
        ),
        median=20_000.0,
        unit="milliseconds",
        is_tie=True,
    )


def test_returns_none_when_scenario_has_no_metrics() -> None:
    """A scenario without measured metrics has no bottleneck candidate."""
    scenario = ScenarioResult(
        scenario_id="empty",
        metrics=(),
    )

    result = identify_bottleneck_candidate(
        scenario=scenario,
        metrics={},
    )

    assert result is None
