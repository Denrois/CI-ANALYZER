"""Integration tests for the validate CLI command."""

from pathlib import Path

import pytest

from ci_experiment_analyzer.cli import main


def test_validate_command_accepts_valid_configuration(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The validate command should accept a valid experiment."""
    data_directory = tmp_path / "data"
    data_directory.mkdir()

    (data_directory / "baseline.csv").write_text(
        "run_id,duration\nbaseline-1,10.0\n",
        encoding="utf-8",
    )
    (data_directory / "optimized.csv").write_text(
        "run_id,duration\noptimized-1,8.0\n",
        encoding="utf-8",
    )

    config_path = tmp_path / "experiment.yaml"
    config_path.write_text(
        """
version: 1

experiment:
  id: validation-example
  title: Validation example

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
  - id: duration
    field: duration
    type: duration
    unit: seconds
    role: total

comparisons:
  - id: duration-impact
    baseline: baseline
    candidate: optimized
    metrics:
      - duration
""".lstrip(),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "validate",
            "--config",
            str(config_path),
        ]
    )

    assert exit_code == 0
    assert (
            "Configuration and data are valid:"
            in capsys.readouterr().out
    )