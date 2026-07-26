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