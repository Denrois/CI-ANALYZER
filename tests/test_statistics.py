"""Tests for statistical calculations."""

import pytest

from ci_experiment_analyzer.comparisons import (
    calculate_relative_difference_percent,
)
from ci_experiment_analyzer.models import (
    MetricConfig,
    RunRecord,
    ScenarioDataset,
)
from ci_experiment_analyzer.statistics import (
    calculate_median,
    calculate_metric_stats,
    calculate_scenario_result,
)


def _duration_metric(
    metric_id: str = "duration",
    role: str = "total",
) -> MetricConfig:
    """Create a duration metric for statistics tests."""
    return MetricConfig(
        id=metric_id,
        field=f"{metric_id}_seconds",
        metric_type="duration",
        unit="seconds",
        role=role,
    )


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


def test_calculate_metric_stats() -> None:
    """All descriptive statistics should be calculated."""
    result = calculate_metric_stats(
        metric=_duration_metric(),
        values=[
            1_000.0,
            2_000.0,
            3_000.0,
            4_000.0,
        ],
    )

    assert result.metric_id == "duration"
    assert result.unit == "milliseconds"
    assert result.role == "total"
    assert result.count == 4
    assert result.median == pytest.approx(2_500.0)
    assert result.mean == pytest.approx(2_500.0)
    assert result.minimum == pytest.approx(1_000.0)
    assert result.maximum == pytest.approx(4_000.0)
    assert result.standard_deviation == pytest.approx(
        1_290.9944487358056
    )


def test_single_value_has_zero_standard_deviation() -> None:
    """One observation should not break statistics calculation."""
    result = calculate_metric_stats(
        metric=_duration_metric(),
        values=[1_500.0],
    )

    assert result.count == 1
    assert result.median == 1_500.0
    assert result.mean == 1_500.0
    assert result.minimum == 1_500.0
    assert result.maximum == 1_500.0
    assert result.standard_deviation == 0.0


def test_metric_stats_reject_empty_sequence() -> None:
    """Statistics must not silently accept an empty sequence."""
    with pytest.raises(
        ValueError,
        match="Cannot calculate statistics for metric 'duration'",
    ):
        calculate_metric_stats(
            metric=_duration_metric(),
            values=[],
        )


def test_calculate_scenario_result_for_all_metrics() -> None:
    """A scenario result should contain every configured metric."""
    dataset = ScenarioDataset(
        scenario_id="baseline",
        records=(
            RunRecord(
                run_id="run-1",
                metric_values={
                    "install_duration": 10_000.0,
                    "total_duration": 50_000.0,
                },
            ),
            RunRecord(
                run_id="run-2",
                metric_values={
                    "install_duration": 14_000.0,
                    "total_duration": 60_000.0,
                },
            ),
        ),
    )

    metrics = (
        _duration_metric(
            metric_id="install_duration",
            role="phase",
        ),
        _duration_metric(
            metric_id="total_duration",
            role="total",
        ),
    )

    result = calculate_scenario_result(
        dataset=dataset,
        metrics=metrics,
    )

    assert result.scenario_id == "baseline"
    assert len(result.metrics) == 2

    install_stats = result.metrics[0]

    assert install_stats.metric_id == "install_duration"
    assert install_stats.role == "phase"
    assert install_stats.count == 2
    assert install_stats.median == pytest.approx(12_000.0)
    assert install_stats.mean == pytest.approx(12_000.0)
    assert install_stats.minimum == pytest.approx(10_000.0)
    assert install_stats.maximum == pytest.approx(14_000.0)
    assert install_stats.standard_deviation == pytest.approx(
        2_828.42712474619
    )

    total_stats = result.metrics[1]

    assert total_stats.metric_id == "total_duration"
    assert total_stats.role == "total"
    assert total_stats.count == 2
    assert total_stats.median == pytest.approx(55_000.0)
    assert total_stats.mean == pytest.approx(55_000.0)
    assert total_stats.minimum == pytest.approx(50_000.0)
    assert total_stats.maximum == pytest.approx(60_000.0)
    assert total_stats.standard_deviation == pytest.approx(
        7_071.067811865475
    )