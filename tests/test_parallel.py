"""Tests for parallel CI branch analysis."""

import pytest

from ci_experiment_analyzer.errors import DataValidationError
from ci_experiment_analyzer.models import (
    ParallelBranchMeasurement,
    ParallelRunGroup,
    RunRecord,
    ScenarioDataset,
)
from ci_experiment_analyzer.parallel import (
    calculate_parallel_run_metrics,
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