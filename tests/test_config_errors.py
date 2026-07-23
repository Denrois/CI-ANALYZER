"""Tests for configuration loading errors."""

from pathlib import Path

import pytest

from ci_experiment_analyzer.config import load_config
from ci_experiment_analyzer.errors import ConfigLoadError


def test_load_config_rejects_missing_file(
    tmp_path: Path,
) -> None:
    """A missing configuration file should produce a clear error."""
    config_path = tmp_path / "missing.yaml"

    with pytest.raises(
        ConfigLoadError,
        match="Cannot read configuration file",
    ):
        load_config(config_path)


def test_load_config_rejects_malformed_yaml(
    tmp_path: Path,
) -> None:
    """Syntactically invalid YAML should produce a clear error."""
    config_path = tmp_path / "invalid.yaml"

    config_path.write_text(
        "version: 1\n"
        "scenarios: [\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ConfigLoadError,
        match="Cannot parse YAML configuration",
    ):
        load_config(config_path)


def test_load_config_rejects_non_mapping_root(
    tmp_path: Path,
) -> None:
    """The root YAML document must be a mapping."""
    config_path = tmp_path / "list-root.yaml"

    config_path.write_text(
        "- value-one\n"
        "- value-two\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ConfigLoadError,
        match="configuration root must be a mapping",
    ):
        load_config(config_path)


def test_load_config_rejects_missing_top_level_field(
    tmp_path: Path,
) -> None:
    """Required top-level configuration sections must exist."""
    config_path = tmp_path / "missing-metrics.yaml"

    config_path.write_text(
        """
version: 1

experiment:
  id: example
  title: Example

scenarios: []

record_mapping:
  run_id: run_id

comparisons: []
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(
        ConfigLoadError,
        match="missing required field 'metrics'",
    ):
        load_config(config_path)


def test_load_config_rejects_wrong_scenarios_type(
    tmp_path: Path,
) -> None:
    """The scenarios section must be a YAML list."""
    config_path = tmp_path / "invalid-scenarios.yaml"

    config_path.write_text(
        """
version: 1

experiment:
  id: example
  title: Example

scenarios:
  id: baseline

record_mapping:
  run_id: run_id

metrics: []
comparisons: []
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(
        ConfigLoadError,
        match="scenarios must be a list",
    ):
        load_config(config_path)


def test_load_config_rejects_non_string_metric_field(
    tmp_path: Path,
) -> None:
    """Metric field names must be strings."""
    config_path = tmp_path / "invalid-metric.yaml"

    config_path.write_text(
        """
version: 1

experiment:
  id: example
  title: Example

scenarios: []

record_mapping:
  run_id: run_id

metrics:
  - id: duration
    field: 123
    type: duration
    unit: seconds
    role: total

comparisons: []
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(
        ConfigLoadError,
        match="field 'field' must be a string",
    ):
        load_config(config_path)

def test_load_config_rejects_non_numeric_analysis_threshold(
    tmp_path: Path,
) -> None:
    """Analysis thresholds must be YAML numbers."""
    config_path = tmp_path / "invalid-threshold.yaml"

    config_path.write_text(
        """
version: 1

experiment:
  id: invalid-threshold
  title: Invalid threshold

scenarios: []

record_mapping:
  run_id: run_id

analysis:
  local_improvement_threshold_pct: invalid

metrics: []
comparisons: []
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(
        ConfigLoadError,
        match=(
            "analysis field "
            "'local_improvement_threshold_pct' "
            "must be a number"
        ),
    ):
        load_config(config_path)