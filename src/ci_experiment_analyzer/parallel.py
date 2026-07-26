"""Analyze measurements from parallel CI branches."""

import math
from collections.abc import Sequence
from statistics import fmean, median, stdev

from ci_experiment_analyzer.errors import DataValidationError
from ci_experiment_analyzer.models import (
    ParallelBranchMeasurement,
    ParallelMetricStats,
    ParallelRunGroup,
    ParallelRunMetrics,
    ParallelScenarioResult,
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


def calculate_parallel_run_metrics(
    run_group: ParallelRunGroup,
) -> ParallelRunMetrics:
    """Calculate duration and imbalance metrics for one parallel run."""
    if not run_group.branches:
        raise DataValidationError(
            f"Parallel run {run_group.run_id!r} "
            "does not contain any branches."
        )

    for branch in run_group.branches:
        if (
            not math.isfinite(branch.duration)
            or branch.duration < 0.0
        ):
            raise DataValidationError(
                f"Parallel run {run_group.run_id!r}, "
                f"branch {branch.branch_id!r} contains "
                f"invalid duration {branch.duration!r}."
            )

    durations = tuple(
        branch.duration
        for branch in run_group.branches
    )

    critical_path_duration = max(durations)
    minimum_branch_duration = min(durations)
    mean_branch_duration = fmean(durations)

    slowest_branch_ids = tuple(
        branch.branch_id
        for branch in run_group.branches
        if math.isclose(
            branch.duration,
            critical_path_duration,
            rel_tol=1e-9,
            abs_tol=1e-9,
        )
    )

    if mean_branch_duration == 0.0:
        imbalance_ratio = 1.0
    else:
        imbalance_ratio = (
            critical_path_duration
            / mean_branch_duration
        )

    return ParallelRunMetrics(
        run_id=run_group.run_id,
        branch_count=len(run_group.branches),
        critical_path_duration=critical_path_duration,
        minimum_branch_duration=minimum_branch_duration,
        mean_branch_duration=mean_branch_duration,
        spread=(
            critical_path_duration
            - minimum_branch_duration
        ),
        imbalance_ratio=imbalance_ratio,
        slowest_branch_ids=slowest_branch_ids,
        is_slowest_tie=len(slowest_branch_ids) > 1,
    )


def _calculate_parallel_metric_stats(
    values: Sequence[float],
    context: str,
) -> ParallelMetricStats:
    """Calculate descriptive statistics for parallel run values."""
    if not values:
        raise DataValidationError(
            f"{context} does not contain any values."
        )

    normalized_values = tuple(
        float(value)
        for value in values
    )

    for value in normalized_values:
        if not math.isfinite(value):
            raise DataValidationError(
                f"{context} contains non-finite value "
                f"{value!r}."
            )

    standard_deviation = (
        stdev(normalized_values)
        if len(normalized_values) > 1
        else 0.0
    )

    return ParallelMetricStats(
        count=len(normalized_values),
        median=float(
            median(normalized_values)
        ),
        mean=fmean(normalized_values),
        minimum=min(normalized_values),
        maximum=max(normalized_values),
        standard_deviation=standard_deviation,
    )


def calculate_parallel_scenario_result(
    scenario_id: str,
    run_metrics: Sequence[ParallelRunMetrics],
    duration_unit: str,
) -> ParallelScenarioResult:
    """Aggregate parallel run metrics for one scenario."""
    runs = tuple(run_metrics)

    if not runs:
        raise DataValidationError(
            f"Parallel scenario {scenario_id!r} "
            "does not contain any analyzed runs."
        )

    if not duration_unit.strip():
        raise DataValidationError(
            f"Parallel scenario {scenario_id!r} "
            "must define a non-empty duration unit."
        )

    seen_run_ids: set[str] = set()

    for run in runs:
        if run.run_id in seen_run_ids:
            raise DataValidationError(
                f"Parallel scenario {scenario_id!r} "
                f"contains duplicate analyzed run "
                f"{run.run_id!r}."
            )

        seen_run_ids.add(run.run_id)

    branch_counts = tuple(
        run.branch_count
        for run in runs
    )

    critical_path_values = tuple(
        run.critical_path_duration
        for run in runs
    )

    spread_values = tuple(
        run.spread
        for run in runs
    )

    imbalance_ratio_values = tuple(
        run.imbalance_ratio
        for run in runs
    )

    branch_count_minimum = min(branch_counts)
    branch_count_maximum = max(branch_counts)

    return ParallelScenarioResult(
        scenario_id=scenario_id,
        duration_unit=duration_unit,
        runs=runs,
        branch_count_minimum=branch_count_minimum,
        branch_count_maximum=branch_count_maximum,
        branch_count_consistent=(
            branch_count_minimum
            == branch_count_maximum
        ),
        critical_path_duration=(
            _calculate_parallel_metric_stats(
                values=critical_path_values,
                context=(
                    f"Parallel scenario {scenario_id!r} "
                    "critical path duration"
                ),
            )
        ),
        spread=_calculate_parallel_metric_stats(
            values=spread_values,
            context=(
                f"Parallel scenario {scenario_id!r} "
                "spread"
            ),
        ),
        imbalance_ratio=_calculate_parallel_metric_stats(
            values=imbalance_ratio_values,
            context=(
                f"Parallel scenario {scenario_id!r} "
                "imbalance ratio"
            ),
        ),
    )