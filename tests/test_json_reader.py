"""Tests for JSON experiment data reading."""

import json
from pathlib import Path

import pytest

from ci_experiment_analyzer.errors import DataValidationError
from ci_experiment_analyzer.models import (
    MetricConfig,
    ScenarioConfig,
    SourceConfig,
)
from ci_experiment_analyzer.readers import read_scenario


def _scenario(json_path: Path) -> ScenarioConfig:
    """Create a JSON scenario configuration."""
    return ScenarioConfig(
        id="baseline",
        source=SourceConfig(
            format="json",
            path=json_path,
        ),
    )


def _metrics() -> tuple[MetricConfig, ...]:
    """Create metrics used by JSON reader tests."""
    return (
        MetricConfig(
            id="install_duration",
            field="dependency_time",
            metric_type="duration",
            unit="seconds",
            role="phase",
        ),
        MetricConfig(
            id="total_duration",
            field="total_time",
            metric_type="duration",
            unit="seconds",
            role="total",
        ),
    )


def test_read_json_scenario_uses_configured_field_names(
    tmp_path: Path,
) -> None:
    """JSON fields should be selected through metric configuration."""
    json_path = tmp_path / "baseline.json"

    json_path.write_text(
        json.dumps(
            [
                {
                    "execution": "run-1",
                    "dependency_time": 10.5,
                    "total_time": 50.0,
                },
                {
                    "execution": "run-2",
                    "dependency_time": 12.5,
                    "total_time": 54.0,
                },
            ]
        ),
        encoding="utf-8",
    )

    dataset = read_scenario(
        scenario=_scenario(json_path),
        metrics=_metrics(),
        record_mapping={"run_id": "execution"},
    )

    assert dataset.scenario_id == "baseline"
    assert len(dataset.records) == 2

    assert dataset.records[0].run_id == "run-1"
    assert dataset.records[0].metric_values == {
        "install_duration": 10_500.0,
        "total_duration": 50_000.0,
    }

    assert dataset.records[1].run_id == "run-2"
    assert dataset.records[1].metric_values == {
        "install_duration": 12_500.0,
        "total_duration": 54_000.0,
    }


def test_json_reader_accepts_numeric_run_id(
    tmp_path: Path,
) -> None:
    """A numeric JSON run identifier should be normalized to text."""
    json_path = tmp_path / "numeric-run-id.json"

    json_path.write_text(
        json.dumps(
            [
                {
                    "execution": 101,
                    "dependency_time": 10.0,
                    "total_time": 50.0,
                }
            ]
        ),
        encoding="utf-8",
    )

    dataset = read_scenario(
        scenario=_scenario(json_path),
        metrics=_metrics(),
        record_mapping={"run_id": "execution"},
    )

    assert dataset.records[0].run_id == "101"


def test_json_reader_rejects_non_list_root(
    tmp_path: Path,
) -> None:
    """A JSON scenario must contain a top-level list."""
    json_path = tmp_path / "object-root.json"

    json_path.write_text(
        json.dumps(
            {
                "execution": "run-1",
                "dependency_time": 10.0,
                "total_time": 50.0,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        DataValidationError,
        match="must contain a top-level list",
    ):
        read_scenario(
            scenario=_scenario(json_path),
            metrics=_metrics(),
            record_mapping={"run_id": "execution"},
        )


def test_json_reader_rejects_non_object_record(
    tmp_path: Path,
) -> None:
    """Every item in a JSON scenario must be an object."""
    json_path = tmp_path / "invalid-record.json"

    json_path.write_text(
        json.dumps(
            [
                {
                    "execution": "run-1",
                    "dependency_time": 10.0,
                    "total_time": 50.0,
                },
                "invalid-record",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        DataValidationError,
        match="record 2, must be an object",
    ):
        read_scenario(
            scenario=_scenario(json_path),
            metrics=_metrics(),
            record_mapping={"run_id": "execution"},
        )


def test_json_reader_rejects_malformed_json(
    tmp_path: Path,
) -> None:
    """Syntactically invalid JSON should produce a clear error."""
    json_path = tmp_path / "malformed.json"

    json_path.write_text(
        '[{"execution": "run-1",',
        encoding="utf-8",
    )

    with pytest.raises(
        DataValidationError,
        match="Cannot parse JSON file",
    ):
        read_scenario(
            scenario=_scenario(json_path),
            metrics=_metrics(),
            record_mapping={"run_id": "execution"},
        )


def test_json_reader_rejects_missing_metric_field(
    tmp_path: Path,
) -> None:
    """Every configured metric field must exist in every record."""
    json_path = tmp_path / "missing-field.json"

    json_path.write_text(
        json.dumps(
            [
                {
                    "execution": "run-1",
                    "dependency_time": 10.0,
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        DataValidationError,
        match="does not contain field 'total_time'",
    ):
        read_scenario(
            scenario=_scenario(json_path),
            metrics=_metrics(),
            record_mapping={"run_id": "execution"},
        )