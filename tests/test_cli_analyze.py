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

    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["version"] == 1
    assert report["experiment"] == {
        "id": "minimal-cache-example",
        "title": "Minimal cache experiment",
    }

    comparison = report["comparisons"][0]

    assert comparison["id"] == "cache-impact"
    assert comparison["baseline"] == "baseline"
    assert comparison["candidate"] == "optimized"

    install_result = comparison["metrics"][0]

    assert install_result["id"] == "install_duration"
    assert install_result["baseline_median"] == pytest.approx(12.0)
    assert install_result["candidate_median"] == pytest.approx(9.0)
    assert install_result["absolute_difference"] == pytest.approx(-3.0)
    assert install_result["relative_difference_percent"] == pytest.approx(
        -25.0
    )

    total_result = comparison["metrics"][1]

    assert total_result["id"] == "total_duration"
    assert total_result["baseline_median"] == pytest.approx(55.0)
    assert total_result["candidate_median"] == pytest.approx(48.0)
    assert total_result["absolute_difference"] == pytest.approx(-7.0)
    assert total_result["relative_difference_percent"] == pytest.approx(
        -12.7272727273
    )

    output = capsys.readouterr().out
    assert "Analysis written to" in output
    assert "analysis.json" in output