"""Tests for parallel CI branch analysis."""

import pytest

from ci_experiment_analyzer.errors import DataValidationError
from ci_experiment_analyzer.models import (
    ParallelAnalysisConfig,
    ParallelBranchMeasurement,
    ParallelMetricStats,
    ParallelRunGroup,
    ParallelRunMetrics,
    ParallelScenarioResult,
    RunRecord,
    ScenarioDataset,
)
from ci_experiment_analyzer.parallel import (
    calculate_parallel_run_metrics,
    calculate_parallel_scenario_result,
    compare_parallel_scenarios,
    group_parallel_runs,
)


def _parallel_record(
    run_id: str,
    branch_id: str | None,
    duration: float,
) -> RunRecord:
    """Create one normalized parallel branch record."""
    return RunRecord(
        run_id=run_id,
        branch_id=branch_id,
        metric_values={
            "branch_duration": duration,
        },
    )


def _parallel_run_group(
    run_id: str,
    branches: tuple[tuple[str, float], ...],
) -> ParallelRunGroup:
    """Create one parallel run group from branch-duration pairs."""
    return ParallelRunGroup(
        run_id=run_id,
        branches=tuple(
            ParallelBranchMeasurement(
                branch_id=branch_id,
                duration=duration,
            )
            for branch_id, duration in branches
        ),
    )


def _calculated_run(
    run_id: str,
    branches: tuple[tuple[str, float], ...],
) -> ParallelRunMetrics:
    """Create calculated metrics for one parallel run."""
    return calculate_parallel_run_metrics(
        _parallel_run_group(
            run_id=run_id,
            branches=branches,
        )
    )


def _parallel_stats(
    value: float,
) -> ParallelMetricStats:
    """Create deterministic aggregated parallel statistics."""
    return ParallelMetricStats(
        count=1,
        median=value,
        mean=value,
        minimum=value,
        maximum=value,
        standard_deviation=0.0,
    )


def _parallel_scenario_result(
    scenario_id: str,
    critical_path_duration: float,
    spread: float,
    imbalance_ratio: float,
    duration_unit: str = "milliseconds",
) -> ParallelScenarioResult:
    """Create one deterministic parallel scenario result."""
    return ParallelScenarioResult(
        scenario_id=scenario_id,
        duration_unit=duration_unit,
        runs=(),
        branch_count_minimum=4,
        branch_count_maximum=4,
        branch_count_consistent=True,
        critical_path_duration=_parallel_stats(
            critical_path_duration
        ),
        spread=_parallel_stats(spread),
        imbalance_ratio=_parallel_stats(
            imbalance_ratio
        ),
    )


def test_groups_parallel_branches_by_run() -> None:
    """Branch records should be grouped by shared run identifier."""
    dataset = ScenarioDataset(
        scenario_id="baseline",
        records=(
            _parallel_record(
                run_id="run-1",
                branch_id="shard-1",
                duration=40_000.0,
            ),
            _parallel_record(
                run_id="run-1",
                branch_id="shard-2",
                duration=35_000.0,
            ),
            _parallel_record(
                run_id="run-2",
                branch_id="shard-1",
                duration=39_000.0,
            ),
            _parallel_record(
                run_id="run-2",
                branch_id="shard-2",
                duration=37_000.0,
            ),
        ),
    )

    result = group_parallel_runs(
        dataset=dataset,
        duration_metric_id="branch_duration",
    )

    assert result == (
        ParallelRunGroup(
            run_id="run-1",
            branches=(
                ParallelBranchMeasurement(
                    branch_id="shard-1",
                    duration=40_000.0,
                ),
                ParallelBranchMeasurement(
                    branch_id="shard-2",
                    duration=35_000.0,
                ),
            ),
        ),
        ParallelRunGroup(
            run_id="run-2",
            branches=(
                ParallelBranchMeasurement(
                    branch_id="shard-1",
                    duration=39_000.0,
                ),
                ParallelBranchMeasurement(
                    branch_id="shard-2",
                    duration=37_000.0,
                ),
            ),
        ),
    )


def test_rejects_duplicate_branch_within_run() -> None:
    """One branch may appear only once inside a CI run."""
    dataset = ScenarioDataset(
        scenario_id="baseline",
        records=(
            _parallel_record(
                run_id="run-1",
                branch_id="shard-1",
                duration=40_000.0,
            ),
            _parallel_record(
                run_id="run-1",
                branch_id="shard-1",
                duration=41_000.0,
            ),
        ),
    )

    with pytest.raises(
        DataValidationError,
        match=(
            "duplicate parallel branch 'shard-1' "
            "for run 'run-1'"
        ),
    ):
        group_parallel_runs(
            dataset=dataset,
            duration_metric_id="branch_duration",
        )


def test_rejects_parallel_record_without_branch_id() -> None:
    """Parallel analysis requires every record to identify a branch."""
    dataset = ScenarioDataset(
        scenario_id="baseline",
        records=(
            _parallel_record(
                run_id="run-1",
                branch_id=None,
                duration=40_000.0,
            ),
        ),
    )

    with pytest.raises(
        DataValidationError,
        match=(
            "run 'run-1' contains a parallel record "
            "without a branch identifier"
        ),
    ):
        group_parallel_runs(
            dataset=dataset,
            duration_metric_id="branch_duration",
        )


def test_rejects_record_without_parallel_duration_metric() -> None:
    """Every grouped branch must contain the configured metric."""
    dataset = ScenarioDataset(
        scenario_id="baseline",
        records=(
            RunRecord(
                run_id="run-1",
                branch_id="shard-1",
                metric_values={
                    "other_metric": 40_000.0,
                },
            ),
        ),
    )

    with pytest.raises(
        DataValidationError,
        match=(
            "branch 'shard-1' does not contain metric "
            "'branch_duration'"
        ),
    ):
        group_parallel_runs(
            dataset=dataset,
            duration_metric_id="branch_duration",
        )


def test_allows_same_branch_id_in_different_runs() -> None:
    """Branch identifiers may repeat across different CI runs."""
    dataset = ScenarioDataset(
        scenario_id="baseline",
        records=(
            _parallel_record(
                run_id="run-1",
                branch_id="shard-1",
                duration=40_000.0,
            ),
            _parallel_record(
                run_id="run-2",
                branch_id="shard-1",
                duration=39_000.0,
            ),
        ),
    )

    result = group_parallel_runs(
        dataset=dataset,
        duration_metric_id="branch_duration",
    )

    assert tuple(
        group.run_id
        for group in result
    ) == (
        "run-1",
        "run-2",
    )


def test_calculates_parallel_run_metrics() -> None:
    """Parallel run metrics should describe duration imbalance."""
    run_group = _parallel_run_group(
        run_id="run-1",
        branches=(
            ("shard-1", 40_000.0),
            ("shard-2", 35_000.0),
            ("shard-3", 42_000.0),
            ("shard-4", 38_000.0),
        ),
    )

    result = calculate_parallel_run_metrics(
        run_group
    )

    assert result.run_id == "run-1"
    assert result.branch_count == 4
    assert result.critical_path_duration == 42_000.0
    assert result.minimum_branch_duration == 35_000.0
    assert result.mean_branch_duration == pytest.approx(
        38_750.0
    )
    assert result.spread == 7_000.0
    assert result.imbalance_ratio == pytest.approx(
        42_000.0 / 38_750.0
    )
    assert result.slowest_branch_ids == (
        "shard-3",
    )
    assert result.is_slowest_tie is False


def test_reports_tied_slowest_branches_in_stable_order() -> None:
    """Equal maximum durations should produce tied slowest branches."""
    run_group = _parallel_run_group(
        run_id="run-1",
        branches=(
            ("shard-1", 40_000.0),
            ("shard-2", 30_000.0),
            ("shard-3", 40_000.0),
        ),
    )

    result = calculate_parallel_run_metrics(
        run_group
    )

    assert result.run_id == "run-1"
    assert result.branch_count == 3
    assert result.critical_path_duration == 40_000.0
    assert result.minimum_branch_duration == 30_000.0
    assert result.mean_branch_duration == pytest.approx(
        110_000.0 / 3
    )
    assert result.spread == 10_000.0
    assert result.imbalance_ratio == pytest.approx(
        40_000.0 / (110_000.0 / 3)
    )
    assert result.slowest_branch_ids == (
        "shard-1",
        "shard-3",
    )
    assert result.is_slowest_tie is True


def test_calculates_balanced_parallel_run() -> None:
    """Equal branch durations should have no spread or imbalance."""
    run_group = _parallel_run_group(
        run_id="balanced-run",
        branches=(
            ("shard-1", 25_000.0),
            ("shard-2", 25_000.0),
            ("shard-3", 25_000.0),
        ),
    )

    result = calculate_parallel_run_metrics(
        run_group
    )

    assert result.critical_path_duration == 25_000.0
    assert result.minimum_branch_duration == 25_000.0
    assert result.mean_branch_duration == 25_000.0
    assert result.spread == 0.0
    assert result.imbalance_ratio == 1.0
    assert result.slowest_branch_ids == (
        "shard-1",
        "shard-2",
        "shard-3",
    )
    assert result.is_slowest_tie is True


def test_zero_duration_branches_are_treated_as_balanced() -> None:
    """All-zero branches should use a neutral imbalance ratio."""
    run_group = _parallel_run_group(
        run_id="zero-run",
        branches=(
            ("shard-1", 0.0),
            ("shard-2", 0.0),
        ),
    )

    result = calculate_parallel_run_metrics(
        run_group
    )

    assert result.critical_path_duration == 0.0
    assert result.minimum_branch_duration == 0.0
    assert result.mean_branch_duration == 0.0
    assert result.spread == 0.0
    assert result.imbalance_ratio == 1.0
    assert result.is_slowest_tie is True


def test_rejects_parallel_run_without_branches() -> None:
    """A parallel run must contain at least one branch."""
    run_group = ParallelRunGroup(
        run_id="empty-run",
        branches=(),
    )

    with pytest.raises(
        DataValidationError,
        match=(
            "Parallel run 'empty-run' does not contain "
            "any branches"
        ),
    ):
        calculate_parallel_run_metrics(
            run_group
        )


def test_rejects_invalid_parallel_branch_duration() -> None:
    """Parallel run calculation requires valid durations."""
    run_group = _parallel_run_group(
        run_id="invalid-run",
        branches=(
            ("shard-1", -1.0),
        ),
    )

    with pytest.raises(
        DataValidationError,
        match=(
            "branch 'shard-1' contains invalid duration"
        ),
    ):
        calculate_parallel_run_metrics(
            run_group
        )


def test_aggregates_parallel_scenario_statistics() -> None:
    """Run-level parallel metrics should be aggregated by scenario."""
    first_run = _calculated_run(
        run_id="run-1",
        branches=(
            ("shard-1", 40_000.0),
            ("shard-2", 35_000.0),
            ("shard-3", 42_000.0),
            ("shard-4", 38_000.0),
        ),
    )

    second_run = _calculated_run(
        run_id="run-2",
        branches=(
            ("shard-1", 39_000.0),
            ("shard-2", 37_000.0),
            ("shard-3", 41_000.0),
            ("shard-4", 36_000.0),
        ),
    )

    result = calculate_parallel_scenario_result(
        scenario_id="baseline",
        run_metrics=(
            first_run,
            second_run,
        ),
        duration_unit="milliseconds",
    )

    assert result.scenario_id == "baseline"
    assert result.duration_unit == "milliseconds"
    assert result.runs == (
        first_run,
        second_run,
    )

    assert result.branch_count_minimum == 4
    assert result.branch_count_maximum == 4
    assert result.branch_count_consistent is True

    critical_path = result.critical_path_duration

    assert critical_path.count == 2
    assert critical_path.median == 41_500.0
    assert critical_path.mean == 41_500.0
    assert critical_path.minimum == 41_000.0
    assert critical_path.maximum == 42_000.0
    assert critical_path.standard_deviation == pytest.approx(
        707.1067811865476
    )

    spread = result.spread

    assert spread.count == 2
    assert spread.median == 6_000.0
    assert spread.mean == 6_000.0
    assert spread.minimum == 5_000.0
    assert spread.maximum == 7_000.0
    assert spread.standard_deviation == pytest.approx(
        1_414.213562373095
    )

    first_ratio = 42_000.0 / 38_750.0
    second_ratio = 41_000.0 / 38_250.0
    expected_ratio_mean = (
        first_ratio + second_ratio
    ) / 2

    imbalance = result.imbalance_ratio

    assert imbalance.count == 2
    assert imbalance.median == pytest.approx(
        expected_ratio_mean
    )
    assert imbalance.mean == pytest.approx(
        expected_ratio_mean
    )
    assert imbalance.minimum == pytest.approx(
        min(first_ratio, second_ratio)
    )
    assert imbalance.maximum == pytest.approx(
        max(first_ratio, second_ratio)
    )

    expected_ratio_standard_deviation = (
        abs(first_ratio - second_ratio)
        / (2 ** 0.5)
    )

    assert (
        imbalance.standard_deviation
        == pytest.approx(
            expected_ratio_standard_deviation
        )
    )


def test_detects_inconsistent_parallel_branch_counts() -> None:
    """Different branch counts across runs should be reported."""
    result = calculate_parallel_scenario_result(
        scenario_id="variable-shards",
        run_metrics=(
            _calculated_run(
                run_id="run-1",
                branches=(
                    ("shard-1", 20_000.0),
                    ("shard-2", 18_000.0),
                ),
            ),
            _calculated_run(
                run_id="run-2",
                branches=(
                    ("shard-1", 20_000.0),
                    ("shard-2", 18_000.0),
                    ("shard-3", 17_000.0),
                ),
            ),
        ),
        duration_unit="milliseconds",
    )

    assert result.branch_count_minimum == 2
    assert result.branch_count_maximum == 3
    assert result.branch_count_consistent is False


def test_single_parallel_run_uses_zero_standard_deviation() -> None:
    """One analyzed run should have zero sample deviation."""
    result = calculate_parallel_scenario_result(
        scenario_id="single-run",
        run_metrics=(
            _calculated_run(
                run_id="run-1",
                branches=(
                    ("shard-1", 25_000.0),
                    ("shard-2", 20_000.0),
                ),
            ),
        ),
        duration_unit="milliseconds",
    )

    assert (
        result.critical_path_duration
        .standard_deviation
        == 0.0
    )
    assert result.spread.standard_deviation == 0.0
    assert (
        result.imbalance_ratio.standard_deviation
        == 0.0
    )

    assert result.branch_count_minimum == 2
    assert result.branch_count_maximum == 2
    assert result.branch_count_consistent is True


def test_rejects_parallel_scenario_without_runs() -> None:
    """A scenario result requires at least one analyzed run."""
    with pytest.raises(
        DataValidationError,
        match=(
            "Parallel scenario 'empty' does not contain "
            "any analyzed runs"
        ),
    ):
        calculate_parallel_scenario_result(
            scenario_id="empty",
            run_metrics=(),
            duration_unit="milliseconds",
        )


def test_rejects_duplicate_parallel_run_results() -> None:
    """Each CI run may appear only once in scenario statistics."""
    run = _calculated_run(
        run_id="run-1",
        branches=(
            ("shard-1", 25_000.0),
            ("shard-2", 20_000.0),
        ),
    )

    with pytest.raises(
        DataValidationError,
        match=(
            "contains duplicate analyzed run 'run-1'"
        ),
    ):
        calculate_parallel_scenario_result(
            scenario_id="baseline",
            run_metrics=(
                run,
                run,
            ),
            duration_unit="milliseconds",
        )


def test_compares_parallel_scenario_medians() -> None:
    """Parallel scenario medians should be compared consistently."""
    analysis = ParallelAnalysisConfig(
        id="test-sharding",
        baseline="baseline",
        candidate="timing-based",
        duration_metric="branch_duration",
    )

    baseline = _parallel_scenario_result(
        scenario_id="baseline",
        critical_path_duration=42_000.0,
        spread=8_000.0,
        imbalance_ratio=1.15,
    )

    candidate = _parallel_scenario_result(
        scenario_id="timing-based",
        critical_path_duration=36_000.0,
        spread=3_000.0,
        imbalance_ratio=1.035,
    )

    result = compare_parallel_scenarios(
        analysis=analysis,
        baseline=baseline,
        candidate=candidate,
    )

    assert tuple(
        metric.metric_id
        for metric in result.metrics
    ) == (
               "critical_path_duration",
               "spread",
               "imbalance_ratio",
           )

    assert result.analysis_id == "test-sharding"
    assert result.duration_metric_id == "branch_duration"
    assert result.baseline is baseline
    assert result.candidate is candidate

    metrics_by_id = {
        metric.metric_id: metric
        for metric in result.metrics
    }

    critical_path = metrics_by_id[
        "critical_path_duration"
    ]

    assert critical_path.unit == "milliseconds"
    assert critical_path.baseline_median == 42_000.0
    assert critical_path.candidate_median == 36_000.0
    assert critical_path.absolute_difference == -6_000.0
    assert (
        critical_path.relative_difference_percent
        == pytest.approx(-14.2857142857)
    )

    spread = metrics_by_id["spread"]

    assert spread.unit == "milliseconds"
    assert spread.baseline_median == 8_000.0
    assert spread.candidate_median == 3_000.0
    assert spread.absolute_difference == -5_000.0
    assert (
        spread.relative_difference_percent
        == pytest.approx(-62.5)
    )

    imbalance = metrics_by_id["imbalance_ratio"]

    assert imbalance.unit == "ratio"
    assert imbalance.baseline_median == pytest.approx(
        1.15
    )
    assert imbalance.candidate_median == pytest.approx(
        1.035
    )
    assert imbalance.absolute_difference == pytest.approx(
        -0.115
    )
    assert (
        imbalance.relative_difference_percent
        == pytest.approx(-10.0)
    )


def test_parallel_comparison_handles_zero_baseline_median() -> None:
    """A zero baseline median should produce no relative change."""
    analysis = ParallelAnalysisConfig(
        id="balanced-to-unbalanced",
        baseline="baseline",
        candidate="candidate",
        duration_metric="branch_duration",
    )

    baseline = _parallel_scenario_result(
        scenario_id="baseline",
        critical_path_duration=20_000.0,
        spread=0.0,
        imbalance_ratio=1.0,
    )

    candidate = _parallel_scenario_result(
        scenario_id="candidate",
        critical_path_duration=21_000.0,
        spread=1_000.0,
        imbalance_ratio=1.05,
    )

    result = compare_parallel_scenarios(
        analysis=analysis,
        baseline=baseline,
        candidate=candidate,
    )

    metrics_by_id = {
        metric.metric_id: metric
        for metric in result.metrics
    }

    spread = metrics_by_id["spread"]

    assert spread.baseline_median == 0.0
    assert spread.candidate_median == 1_000.0
    assert spread.absolute_difference == 1_000.0
    assert spread.relative_difference_percent is None


def test_parallel_comparison_rejects_wrong_baseline() -> None:
    """Configured baseline must match the supplied result."""
    analysis = ParallelAnalysisConfig(
        id="test-sharding",
        baseline="baseline",
        candidate="candidate",
        duration_metric="branch_duration",
    )

    wrong_baseline = _parallel_scenario_result(
        scenario_id="other",
        critical_path_duration=20_000.0,
        spread=2_000.0,
        imbalance_ratio=1.1,
    )

    candidate = _parallel_scenario_result(
        scenario_id="candidate",
        critical_path_duration=18_000.0,
        spread=1_000.0,
        imbalance_ratio=1.05,
    )

    with pytest.raises(
        DataValidationError,
        match=(
            "expected baseline scenario 'baseline', "
            "but received 'other'"
        ),
    ):
        compare_parallel_scenarios(
            analysis=analysis,
            baseline=wrong_baseline,
            candidate=candidate,
        )


def test_parallel_comparison_rejects_different_units() -> None:
    """Parallel duration results must use the same unit."""
    analysis = ParallelAnalysisConfig(
        id="test-sharding",
        baseline="baseline",
        candidate="candidate",
        duration_metric="branch_duration",
    )

    baseline = _parallel_scenario_result(
        scenario_id="baseline",
        critical_path_duration=20_000.0,
        spread=2_000.0,
        imbalance_ratio=1.1,
        duration_unit="milliseconds",
    )

    candidate = _parallel_scenario_result(
        scenario_id="candidate",
        critical_path_duration=18.0,
        spread=1.0,
        imbalance_ratio=1.05,
        duration_unit="seconds",
    )

    with pytest.raises(
        DataValidationError,
        match="different duration units",
    ):
        compare_parallel_scenarios(
            analysis=analysis,
            baseline=baseline,
            candidate=candidate,
        )