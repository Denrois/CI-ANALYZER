"""Integration tests for configured parallel analysis."""

from pathlib import Path
from typing import Any, cast

import pytest

from ci_experiment_analyzer.analyzer import (
    analyze_experiment,
)
from ci_experiment_analyzer.config import load_config
from ci_experiment_analyzer.reports import (
    analysis_result_to_dict,
)
from ci_experiment_analyzer.validation import (
    validate_config,
)


def test_analyzes_parallel_scenarios_end_to_end(
    tmp_path: Path,
) -> None:
    """Configured CSV data should produce a parallel report."""
    baseline_path = tmp_path / "baseline.csv"
    candidate_path = tmp_path / "candidate.csv"
    config_path = tmp_path / "experiment.yaml"

    baseline_path.write_text(
        (
            "workflow_run_id,shard_id,"
            "shard_duration_seconds\n"
            "baseline-1,shard-1,40\n"
            "baseline-1,shard-2,20\n"
            "baseline-2,shard-1,30\n"
            "baseline-2,shard-2,10\n"
        ),
        encoding="utf-8",
    )

    candidate_path.write_text(
        (
            "workflow_run_id,shard_id,"
            "shard_duration_seconds\n"
            "candidate-1,shard-1,30\n"
            "candidate-1,shard-2,30\n"
            "candidate-2,shard-1,20\n"
            "candidate-2,shard-2,20\n"
        ),
        encoding="utf-8",
    )

    config_path.write_text(
        """
version: 1

experiment:
  id: parallel-stage-example
  title: Parallel stage example

scenarios:
  - id: baseline
    source:
      format: csv
      path: baseline.csv

  - id: timing-based
    source:
      format: csv
      path: candidate.csv

record_mapping:
  run_id: workflow_run_id
  branch_id: shard_id

metrics:
  - id: shard_duration
    field: shard_duration_seconds
    type: duration
    unit: seconds
    role: parallel_branch

comparisons: []

parallel_analyses:
  - id: test-sharding
    baseline: baseline
    candidate: timing-based
    duration_metric: shard_duration
""".lstrip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    validate_config(config)

    result = analyze_experiment(config)

    assert len(result.parallel_analyses) == 1

    parallel_result = result.parallel_analyses[0]

    assert parallel_result.analysis_id == "test-sharding"
    assert parallel_result.duration_metric_id == "shard_duration"

    assert parallel_result.baseline.scenario_id == "baseline"
    assert parallel_result.candidate.scenario_id == "timing-based"

    assert parallel_result.baseline.critical_path_duration.median == 35_000.0
    assert parallel_result.candidate.critical_path_duration.median == 25_000.0

    assert parallel_result.baseline.spread.median == (20_000.0)
    assert parallel_result.candidate.spread.median == (0.0)

    report = analysis_result_to_dict(result)

    parallel_analyses = cast(
        list[dict[str, Any]],
        report["parallel_analyses"],
    )

    assert len(parallel_analyses) == 1

    parallel_report = parallel_analyses[0]

    assert parallel_report["id"] == "test-sharding"
    assert parallel_report["duration_metric"] == "shard_duration"

    baseline_report = cast(
        dict[str, Any],
        parallel_report["baseline"],
    )
    candidate_report = cast(
        dict[str, Any],
        parallel_report["candidate"],
    )

    assert baseline_report["scenario"] == "baseline"
    assert candidate_report["scenario"] == ("timing-based")

    assert baseline_report["branch_count"] == {
        "minimum": 2,
        "maximum": 2,
        "consistent": True,
    }
    assert candidate_report["branch_count"] == {
        "minimum": 2,
        "maximum": 2,
        "consistent": True,
    }

    baseline_runs = cast(
        list[dict[str, Any]],
        baseline_report["runs"],
    )
    candidate_runs = cast(
        list[dict[str, Any]],
        candidate_report["runs"],
    )

    assert len(baseline_runs) == 2
    assert len(candidate_runs) == 2

    assert baseline_runs[0]["run_id"] == "baseline-1"
    assert baseline_runs[0]["branch_count"] == 2
    assert baseline_runs[0]["critical_path_duration"] == 40_000.0
    assert baseline_runs[0]["minimum_branch_duration"] == 20_000.0
    assert baseline_runs[0]["mean_branch_duration"] == 30_000.0
    assert baseline_runs[0]["spread"] == 20_000.0
    assert baseline_runs[0]["imbalance_ratio"] == (pytest.approx(4.0 / 3.0))
    assert baseline_runs[0]["slowest_branches"] == [
        "shard-1",
    ]
    assert baseline_runs[0]["is_slowest_tie"] is False

    assert candidate_runs[0]["run_id"] == ("candidate-1")
    assert candidate_runs[0]["critical_path_duration"] == 30_000.0
    assert candidate_runs[0]["spread"] == 0.0
    assert candidate_runs[0]["imbalance_ratio"] == (1.0)
    assert candidate_runs[0]["slowest_branches"] == [
        "shard-1",
        "shard-2",
    ]
    assert candidate_runs[0]["is_slowest_tie"] is True

    metric_reports = cast(
        list[dict[str, Any]],
        parallel_report["metrics"],
    )

    metrics_by_id = {metric["id"]: metric for metric in metric_reports}

    critical_path = metrics_by_id["critical_path_duration"]

    assert critical_path["unit"] == "milliseconds"
    assert critical_path["baseline_median"] == (35_000.0)
    assert critical_path["candidate_median"] == (25_000.0)
    assert critical_path["absolute_difference"] == (-10_000.0)
    assert critical_path["relative_difference_percent"] == pytest.approx(-28.5714285714)

    spread = metrics_by_id["spread"]

    assert spread["unit"] == "milliseconds"
    assert spread["baseline_median"] == 20_000.0
    assert spread["candidate_median"] == 0.0
    assert spread["absolute_difference"] == -20_000.0
    assert spread["relative_difference_percent"] == -100.0

    imbalance = metrics_by_id["imbalance_ratio"]

    assert imbalance["unit"] == "ratio"
    assert imbalance["baseline_median"] == (pytest.approx(17.0 / 12.0))
    assert imbalance["candidate_median"] == 1.0
    assert imbalance["absolute_difference"] == (pytest.approx(-5.0 / 12.0))
    assert imbalance["relative_difference_percent"] == pytest.approx(-500.0 / 17.0)
