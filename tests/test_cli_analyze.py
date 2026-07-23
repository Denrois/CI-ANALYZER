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