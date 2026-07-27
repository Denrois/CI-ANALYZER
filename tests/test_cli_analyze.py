"""Integration tests for the analyze CLI command."""

import json
from pathlib import Path

import pytest

from ci_experiment_analyzer.cli import main


def test_analyze_command_writes_json_report(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI should analyze configured CSV scenarios end to end."""
    data_directory = tmp_path / "data"
    data_directory.mkdir()

    baseline_path = data_directory / "baseline.csv"
    baseline_path.write_text(
        (
            "run_id,install_seconds,total_seconds\n"
            "baseline-1,10.0,50.0\n"
            "baseline-2,14.0,60.0\n"
        ),
        encoding="utf-8",
    )

    optimized_path = data_directory / "optimized.csv"
    optimized_path.write_text(
        (
            "run_id,install_seconds,total_seconds\n"
            "optimized-1,8.0,45.0\n"
            "optimized-2,10.0,51.0\n"
        ),
        encoding="utf-8",
    )

    config_path = tmp_path / "experiment.yaml"
    config_path.write_text(
        """
version: 1

experiment:
  id: minimal-cache-example
  title: Minimal cache experiment

scenarios:
  - id: baseline
    source:
      format: csv
      path: data/baseline.csv

  - id: optimized
    source:
      format: csv
      path: data/optimized.csv

record_mapping:
  run_id: run_id

analysis:
  local_improvement_threshold_pct: 10.0
  total_impact_threshold_pct: 15.0

metrics:
  - id: install_duration
    field: install_seconds
    type: duration
    unit: seconds
    role: phase

  - id: total_duration
    field: total_seconds
    type: duration
    unit: seconds
    role: total

comparisons:
  - id: cache-impact
    baseline: baseline
    candidate: optimized
    metrics:
      - install_duration
      - total_duration
""".lstrip(),
        encoding="utf-8",
    )

    output_directory = tmp_path / "report"

    exit_code = main(
        [
            "analyze",
            "--config",
            str(config_path),
            "--output",
            str(output_directory),
        ]
    )

    assert exit_code == 0

    report_path = output_directory / "analysis.json"

    assert report_path.is_file()

    report = json.loads(
        report_path.read_text(encoding="utf-8")
    )

    assert report["version"] == 1
    assert report["experiment"] == {
        "id": "minimal-cache-example",
        "title": "Minimal cache experiment",
    }

    assert len(report["comparisons"]) == 1

    comparison = report["comparisons"][0]

    assert comparison["id"] == "cache-impact"
    assert comparison["baseline"] == "baseline"
    assert comparison["candidate"] == "optimized"

    assert len(comparison["metrics"]) == 2

    install_result = comparison["metrics"][0]

    assert install_result["id"] == "install_duration"
    assert install_result["unit"] == "milliseconds"
    assert install_result["baseline_median"] == pytest.approx(
        12_000.0
    )
    assert install_result["candidate_median"] == pytest.approx(
        9_000.0
    )
    assert install_result["absolute_difference"] == pytest.approx(
        -3_000.0
    )
    assert install_result[
        "relative_difference_percent"
    ] == pytest.approx(-25.0)

    total_result = comparison["metrics"][1]

    assert total_result["id"] == "total_duration"
    assert total_result["unit"] == "milliseconds"
    assert total_result["baseline_median"] == pytest.approx(
        55_000.0
    )
    assert total_result["candidate_median"] == pytest.approx(
        48_000.0
    )
    assert total_result["absolute_difference"] == pytest.approx(
        -7_000.0
    )
    assert total_result[
        "relative_difference_percent"
    ] == pytest.approx(-12.7272727273)

    assert len(report["local_vs_total_impacts"]) == 1

    impact_result = report["local_vs_total_impacts"][0]

    assert impact_result["comparison"] == "cache-impact"
    assert impact_result["phase_metric"] == "install_duration"
    assert impact_result["total_metric"] == "total_duration"

    assert impact_result[
               "phase_relative_difference_percent"
           ] == pytest.approx(-25.0)

    assert impact_result[
               "total_relative_difference_percent"
           ] == pytest.approx(-12.7272727273)

    assert impact_result[
               "local_improvement_threshold_pct"
           ] == pytest.approx(10.0)

    assert impact_result[
               "total_impact_threshold_pct"
           ] == pytest.approx(15.0)

    assert impact_result[
               "substantial_local_improvement"
           ] is True

    assert impact_result[
               "limited_total_improvement"
           ] is True

    assert impact_result[
               "limited_end_to_end_impact"
           ] is True

    assert impact_result["warning"] == (
        "The local phase improved substantially, but the total pipeline "
        "improvement remained below the configured threshold."
    )

    assert len(report["bottleneck_candidates"]) == 2

    baseline_candidate = report[
        "bottleneck_candidates"
    ][0]

    assert baseline_candidate["scenario"] == "baseline"
    assert baseline_candidate["phase_metrics"] == [
        "install_duration",
    ]
    assert baseline_candidate["median"] == pytest.approx(
        12_000.0
    )
    assert baseline_candidate["unit"] == "milliseconds"
    assert baseline_candidate["is_tie"] is False

    optimized_candidate = report[
        "bottleneck_candidates"
    ][1]

    assert optimized_candidate["scenario"] == "optimized"
    assert optimized_candidate["phase_metrics"] == [
        "install_duration",
    ]
    assert optimized_candidate["median"] == pytest.approx(
        9_000.0
    )
    assert optimized_candidate["unit"] == "milliseconds"
    assert optimized_candidate["is_tie"] is False

    assert report["parallel_analyses"] == []

    output = capsys.readouterr().out

    assert "Analysis written to" in output
    assert "analysis.json" in output


def test_analyze_handles_single_run_and_zero_baseline(
    tmp_path: Path,
) -> None:
    """Single-run scenarios and zero baseline should be handled safely."""
    data_directory = tmp_path / "data"
    data_directory.mkdir()

    baseline_path = data_directory / "baseline.csv"
    baseline_path.write_text(
        (
            "run_id,total_seconds\n"
            "baseline-1,0.0\n"
        ),
        encoding="utf-8",
    )

    optimized_path = data_directory / "optimized.csv"
    optimized_path.write_text(
        (
            "run_id,total_seconds\n"
            "optimized-1,1.0\n"
        ),
        encoding="utf-8",
    )

    config_path = tmp_path / "experiment.yaml"
    config_path.write_text(
        """
version: 1

experiment:
  id: statistical-edge-cases
  title: Statistical edge cases

scenarios:
  - id: baseline
    source:
      format: csv
      path: data/baseline.csv

  - id: optimized
    source:
      format: csv
      path: data/optimized.csv

record_mapping:
  run_id: run_id

metrics:
  - id: total_duration
    field: total_seconds
    type: duration
    unit: seconds
    role: total

comparisons:
  - id: zero-baseline-impact
    baseline: baseline
    candidate: optimized
    metrics:
      - total_duration
""".lstrip(),
        encoding="utf-8",
    )

    output_directory = tmp_path / "report"

    exit_code = main(
        [
            "analyze",
            "--config",
            str(config_path),
            "--output",
            str(output_directory),
        ]
    )

    assert exit_code == 0

    report_path = output_directory / "analysis.json"
    report = json.loads(
        report_path.read_text(encoding="utf-8")
    )

    baseline_metric = report["scenarios"][0]["metrics"][0]
    optimized_metric = report["scenarios"][1]["metrics"][0]

    assert baseline_metric == {
        "id": "total_duration",
        "unit": "milliseconds",
        "role": "total",
        "count": 1,
        "median": 0.0,
        "mean": 0.0,
        "minimum": 0.0,
        "maximum": 0.0,
        "standard_deviation": 0.0,
    }

    assert optimized_metric == {
        "id": "total_duration",
        "unit": "milliseconds",
        "role": "total",
        "count": 1,
        "median": 1_000.0,
        "mean": 1_000.0,
        "minimum": 1_000.0,
        "maximum": 1_000.0,
        "standard_deviation": 0.0,
    }

    comparison_metric = report["comparisons"][0]["metrics"][0]

    assert comparison_metric == {
        "id": "total_duration",
        "unit": "milliseconds",
        "baseline_median": 0.0,
        "candidate_median": 1_000.0,
        "absolute_difference": 1_000.0,
        "relative_difference_percent": None,
    }

    assert report["local_vs_total_impacts"] == []

    assert report["bottleneck_candidates"] == []

    assert report["parallel_analyses"] == []


def test_analyze_command_writes_parallel_analysis_report(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI should analyze parallel branch data end to end."""
    data_directory = tmp_path / "data"
    data_directory.mkdir()

    baseline_path = data_directory / "baseline.csv"
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

    candidate_path = data_directory / "candidate.csv"
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

    config_path = tmp_path / "experiment.yaml"
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
      path: data/baseline.csv

  - id: timing-based
    source:
      format: csv
      path: data/candidate.csv

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

    output_directory = tmp_path / "report"

    exit_code = main(
        [
            "analyze",
            "--config",
            str(config_path),
            "--output",
            str(output_directory),
        ]
    )

    assert exit_code == 0

    report_path = output_directory / "analysis.json"

    assert report_path.is_file()

    report = json.loads(
        report_path.read_text(encoding="utf-8")
    )

    assert report["experiment"] == {
        "id": "parallel-stage-example",
        "title": "Parallel stage example",
    }

    assert report["comparisons"] == []
    assert report["local_vs_total_impacts"] == []
    assert report["bottleneck_candidates"] == []

    assert len(report["parallel_analyses"]) == 1

    parallel_analysis = report["parallel_analyses"][0]

    assert parallel_analysis["id"] == "test-sharding"
    assert (
        parallel_analysis["duration_metric"]
        == "shard_duration"
    )

    baseline = parallel_analysis["baseline"]
    candidate = parallel_analysis["candidate"]

    assert baseline["scenario"] == "baseline"
    assert candidate["scenario"] == "timing-based"

    assert baseline["duration_unit"] == "milliseconds"
    assert candidate["duration_unit"] == "milliseconds"

    assert baseline["branch_count"] == {
        "minimum": 2,
        "maximum": 2,
        "consistent": True,
    }
    assert candidate["branch_count"] == {
        "minimum": 2,
        "maximum": 2,
        "consistent": True,
    }

    assert len(baseline["runs"]) == 2
    assert len(candidate["runs"]) == 2

    first_baseline_run = baseline["runs"][0]

    assert first_baseline_run["run_id"] == "baseline-1"
    assert first_baseline_run["branch_count"] == 2
    assert (
        first_baseline_run["critical_path_duration"]
        == 40_000.0
    )
    assert (
        first_baseline_run["minimum_branch_duration"]
        == 20_000.0
    )
    assert (
        first_baseline_run["mean_branch_duration"]
        == 30_000.0
    )
    assert first_baseline_run["spread"] == 20_000.0
    assert (
        first_baseline_run["imbalance_ratio"]
        == pytest.approx(4.0 / 3.0)
    )
    assert first_baseline_run["slowest_branches"] == [
        "shard-1",
    ]
    assert first_baseline_run["is_slowest_tie"] is False

    first_candidate_run = candidate["runs"][0]

    assert first_candidate_run["run_id"] == "candidate-1"
    assert (
        first_candidate_run["critical_path_duration"]
        == 30_000.0
    )
    assert first_candidate_run["spread"] == 0.0
    assert first_candidate_run["imbalance_ratio"] == 1.0
    assert first_candidate_run["slowest_branches"] == [
        "shard-1",
        "shard-2",
    ]
    assert first_candidate_run["is_slowest_tie"] is True

    assert (
        baseline["critical_path_duration"]["median"]
        == 35_000.0
    )
    assert (
        candidate["critical_path_duration"]["median"]
        == 25_000.0
    )

    assert baseline["spread"]["median"] == 20_000.0
    assert candidate["spread"]["median"] == 0.0

    assert (
        baseline["imbalance_ratio"]["median"]
        == pytest.approx(17.0 / 12.0)
    )
    assert candidate["imbalance_ratio"]["median"] == 1.0

    assert tuple(
        metric["id"]
        for metric in parallel_analysis["metrics"]
    ) == (
        "critical_path_duration",
        "spread",
        "imbalance_ratio",
    )

    metrics_by_id = {
        metric["id"]: metric
        for metric in parallel_analysis["metrics"]
    }

    critical_path = metrics_by_id[
        "critical_path_duration"
    ]

    assert critical_path["unit"] == "milliseconds"
    assert critical_path["baseline_median"] == 35_000.0
    assert critical_path["candidate_median"] == 25_000.0
    assert critical_path["absolute_difference"] == (
        -10_000.0
    )
    assert (
        critical_path["relative_difference_percent"]
        == pytest.approx(-28.5714285714)
    )

    spread = metrics_by_id["spread"]

    assert spread["unit"] == "milliseconds"
    assert spread["baseline_median"] == 20_000.0
    assert spread["candidate_median"] == 0.0
    assert spread["absolute_difference"] == -20_000.0
    assert spread["relative_difference_percent"] == -100.0

    imbalance = metrics_by_id["imbalance_ratio"]

    assert imbalance["unit"] == "ratio"
    assert (
        imbalance["baseline_median"]
        == pytest.approx(17.0 / 12.0)
    )
    assert imbalance["candidate_median"] == 1.0
    assert (
        imbalance["absolute_difference"]
        == pytest.approx(-5.0 / 12.0)
    )
    assert (
        imbalance["relative_difference_percent"]
        == pytest.approx(-500.0 / 17.0)
    )

    output = capsys.readouterr().out

    assert "Analysis written to" in output
    assert str(report_path) in output