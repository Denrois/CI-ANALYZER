"""Tests for experiment configuration validation."""

from dataclasses import replace
from pathlib import Path

import pytest

from ci_experiment_analyzer.errors import ConfigValidationError
from ci_experiment_analyzer.models import (
    ComparisonConfig,
    ExperimentConfig,
    ExperimentMetadata,
    MetricConfig,
    ScenarioConfig,
    SourceConfig,
)
from ci_experiment_analyzer.validation import validate_config


def _valid_config(tmp_path: Path) -> ExperimentConfig:
    """Create a valid configuration for validation tests."""
    baseline_path = tmp_path / "baseline.csv"
    optimized_path = tmp_path / "optimized.csv"

    baseline_path.write_text(
        "run_id,duration\nbaseline-1,10.0\n",
        encoding="utf-8",
    )
    optimized_path.write_text(
        "run_id,duration\noptimized-1,8.0\n",
        encoding="utf-8",
    )

    return ExperimentConfig(
        version=1,
        experiment=ExperimentMetadata(
            id="example",
            title="Example experiment",
        ),
        scenarios=(
            ScenarioConfig(
                id="baseline",
                source=SourceConfig(
                    format="csv",
                    path=baseline_path,
                ),
            ),
            ScenarioConfig(
                id="optimized",
                source=SourceConfig(
                    format="csv",
                    path=optimized_path,
                ),
            ),
        ),
        record_mapping={"run_id": "run_id"},
        metrics=(
            MetricConfig(
                id="duration",
                field="duration",
                metric_type="duration",
                unit="seconds",
                role="total",
            ),
        ),
        comparisons=(
            ComparisonConfig(
                id="duration-impact",
                baseline="baseline",
                candidate="optimized",
                metrics=("duration",),
            ),
        ),
    )


def test_validate_config_accepts_valid_configuration(
    tmp_path: Path,
) -> None:
    """A complete and consistent configuration should be accepted."""
    validate_config(_valid_config(tmp_path))


def test_validate_config_rejects_duplicate_scenario_ids(
    tmp_path: Path,
) -> None:
    """Scenario identifiers must be unique."""
    config = _valid_config(tmp_path)

    duplicate_scenario = replace(
        config.scenarios[1],
        id="baseline",
    )
    invalid_config = replace(
        config,
        scenarios=(
            config.scenarios[0],
            duplicate_scenario,
        ),
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        validate_config(invalid_config)

    assert "duplicate scenario id: 'baseline'" in str(exc_info.value)


def test_validate_config_rejects_unknown_comparison_metric(
    tmp_path: Path,
) -> None:
    """Comparisons may only reference configured metrics."""
    config = _valid_config(tmp_path)

    invalid_comparison = replace(
        config.comparisons[0],
        metrics=("unknown-duration",),
    )
    invalid_config = replace(
        config,
        comparisons=(invalid_comparison,),
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        validate_config(invalid_config)

    assert (
        "references unknown metric 'unknown-duration'"
        in str(exc_info.value)
    )


def test_validate_config_rejects_missing_source_file(
    tmp_path: Path,
) -> None:
    """Every scenario source file must exist."""
    config = _valid_config(tmp_path)

    missing_source = replace(
        config.scenarios[0].source,
        path=tmp_path / "missing.csv",
    )
    invalid_scenario = replace(
        config.scenarios[0],
        source=missing_source,
    )
    invalid_config = replace(
        config,
        scenarios=(
            invalid_scenario,
            config.scenarios[1],
        ),
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        validate_config(invalid_config)

    assert "does not exist" in str(exc_info.value)


def test_validate_config_rejects_invalid_duration_unit(
    tmp_path: Path,
) -> None:
    """Duration metrics must use a supported time unit."""
    config = _valid_config(tmp_path)

    invalid_metric = replace(
        config.metrics[0],
        unit="hours",
    )
    invalid_config = replace(
        config,
        metrics=(invalid_metric,),
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        validate_config(invalid_config)

    assert "unsupported unit 'hours'" in str(exc_info.value)


def test_validate_config_accepts_json_source_format(
    tmp_path: Path,
) -> None:
    """JSON should be accepted as a supported scenario source format."""
    config = _valid_config(tmp_path)

    json_path = tmp_path / "baseline.json"
    json_path.write_text(
        "[]",
        encoding="utf-8",
    )

    json_source = replace(
        config.scenarios[0].source,
        format="json",
        path=json_path,
    )
    json_scenario = replace(
        config.scenarios[0],
        source=json_source,
    )
    json_config = replace(
        config,
        scenarios=(
            json_scenario,
            config.scenarios[1],
        ),
    )

    validate_config(json_config)


def test_validate_config_accepts_jsonl_source_format(
    tmp_path: Path,
) -> None:
    """JSONL should be accepted as a scenario source format."""
    config = _valid_config(tmp_path)

    jsonl_path = tmp_path / "baseline.jsonl"
    jsonl_path.write_text(
        (
            '{"run_id":"baseline-1",'
            '"duration":10.0}\n'
        ),
        encoding="utf-8",
    )

    jsonl_source = replace(
        config.scenarios[0].source,
        format="jsonl",
        path=jsonl_path,
    )
    jsonl_scenario = replace(
        config.scenarios[0],
        source=jsonl_source,
    )
    jsonl_config = replace(
        config,
        scenarios=(
            jsonl_scenario,
            config.scenarios[1],
        ),
    )

    validate_config(jsonl_config)