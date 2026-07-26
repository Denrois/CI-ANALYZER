"""Analyze measurements from parallel CI branches."""

from ci_experiment_analyzer.errors import DataValidationError
from ci_experiment_analyzer.models import (
    ParallelBranchMeasurement,
    ParallelRunGroup,
    ScenarioDataset,
)


def group_parallel_runs(
    dataset: ScenarioDataset,
    duration_metric_id: str,
) -> tuple[ParallelRunGroup, ...]:
    """Group parallel branch records by their CI run identifier."""
    grouped_branches: dict[
        str,
        list[ParallelBranchMeasurement],
    ] = {}
    seen_branches: set[tuple[str, str]] = set()

    for record in dataset.records:
        if (
            record.branch_id is None
            or not record.branch_id.strip()
        ):
            raise DataValidationError(
                f"Scenario {dataset.scenario_id!r}, "
                f"run {record.run_id!r} contains a "
                "parallel record without a branch identifier."
            )

        branch_key = (
            record.run_id,
            record.branch_id,
        )

        if branch_key in seen_branches:
            raise DataValidationError(
                f"Scenario {dataset.scenario_id!r} "
                f"contains duplicate parallel branch "
                f"{record.branch_id!r} for run "
                f"{record.run_id!r}."
            )

        try:
            duration = record.metric_values[
                duration_metric_id
            ]
        except KeyError as error:
            raise DataValidationError(
                f"Scenario {dataset.scenario_id!r}, "
                f"run {record.run_id!r}, branch "
                f"{record.branch_id!r} does not contain "
                f"metric {duration_metric_id!r}."
            ) from error

        seen_branches.add(branch_key)

        grouped_branches.setdefault(
            record.run_id,
            [],
        ).append(
            ParallelBranchMeasurement(
                branch_id=record.branch_id,
                duration=duration,
            )
        )

    return tuple(
        ParallelRunGroup(
            run_id=run_id,
            branches=tuple(branches),
        )
        for run_id, branches in grouped_branches.items()
    )