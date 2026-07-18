"""Tests for YAML experiment configuration loading."""

from pathlib import Path

from ci_experiment_analyzer.config import load_config


def test_load_config_from_yaml(tmp_path: Path) -> None:
    """A valid YAML file should produce typed configuration models."""
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

    config = load_config(config_path)

    assert config.version == 1
    assert config.experiment.id == "minimal-cache-example"
    assert config.experiment.title == "Minimal cache experiment"

    assert len(config.scenarios) == 2
    assert config.scenarios[0].id == "baseline"
    assert config.scenarios[0].source.format == "csv"
    assert config.scenarios[0].source.path == (
        tmp_path / "data" / "baseline.csv"
    ).resolve()

    assert config.record_mapping["run_id"] == "run_id"

    assert len(config.metrics) == 2
    assert config.metrics[0].id == "install_duration"
    assert config.metrics[0].field == "install_seconds"

    assert len(config.comparisons) == 1
    assert config.comparisons[0].baseline == "baseline"
    assert config.comparisons[0].candidate == "optimized"
    assert config.comparisons[0].metrics == (
        "install_duration",
        "total_duration",
    )