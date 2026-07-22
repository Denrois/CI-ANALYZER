"""Tests for JSONL experiment data reading."""

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


def _scenario(jsonl_path: Path) -> ScenarioConfig:
    """Create a JSONL scenario configuration."""
    return ScenarioConfig(
        id="baseline",
        source=SourceConfig(
            format="jsonl",
            path=jsonl_path,
        ),
    )


def _metrics() -> tuple[MetricConfig, ...]:
    """Create metrics used by JSONL reader tests."""
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


def test_read_jsonl_scenario_uses_configured_field_names(
    tmp_path: Path,
) -> None:
    """JSONL fields should be selected through configuration."""
    jsonl_path = tmp_path / "baseline.jsonl"

    records = [
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

    jsonl_path.write_text(
        "\n".join(
            json.dumps(record)
            for record in records
        )
        + "\n",
        encoding="utf-8",
    )

    dataset = read_scenario(
        scenario=_scenario(jsonl_path),
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


def test_jsonl_reader_ignores_blank_lines(
    tmp_path: Path,
) -> None:
    """Blank lines between JSONL records should be ignored."""
    jsonl_path = tmp_path / "blank-lines.jsonl"

    jsonl_path.write_text(
        (
            '{"execution":"run-1",'
            '"dependency_time":10.0,'
            '"total_time":50.0}\n'
            "\n"
            "   \n"
            '{"execution":"run-2",'
            '"dependency_time":12.0,'
            '"total_time":54.0}\n'
        ),
        encoding="utf-8",
    )

    dataset = read_scenario(
        scenario=_scenario(jsonl_path),
        metrics=_metrics(),
        record_mapping={"run_id": "execution"},
    )

    assert len(dataset.records) == 2
    assert dataset.records[0].run_id == "run-1"
    assert dataset.records[1].run_id == "run-2"


def test_jsonl_reader_rejects_malformed_line(
    tmp_path: Path,
) -> None:
    """Invalid JSONL syntax should report the physical line."""
    jsonl_path = tmp_path / "malformed.jsonl"

    jsonl_path.write_text(
        (
            '{"execution":"run-1",'
            '"dependency_time":10.0,'
            '"total_time":50.0}\n'
            '{"execution":"run-2",\n'
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        DataValidationError,
        match=r"line 2",
    ):
        read_scenario(
            scenario=_scenario(jsonl_path),
            metrics=_metrics(),
            record_mapping={"run_id": "execution"},
        )


def test_jsonl_reader_rejects_non_object_line(
    tmp_path: Path,
) -> None:
    """Every non-empty JSONL line must contain an object."""
    jsonl_path = tmp_path / "non-object.jsonl"

    jsonl_path.write_text(
        (
            '{"execution":"run-1",'
            '"dependency_time":10.0,'
            '"total_time":50.0}\n'
            '"invalid-record"\n'
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        DataValidationError,
        match=r"line 2 must be an object",
    ):
        read_scenario(
            scenario=_scenario(jsonl_path),
            metrics=_metrics(),
            record_mapping={"run_id": "execution"},
        )


def test_jsonl_reader_rejects_missing_metric_field(
    tmp_path: Path,
) -> None:
    """Every JSONL record must contain configured metric fields."""
    jsonl_path = tmp_path / "missing-field.jsonl"

    jsonl_path.write_text(
        (
            '{"execution":"run-1",'
            '"dependency_time":10.0}\n'
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        DataValidationError,
        match="does not contain field 'total_time'",
    ):
        read_scenario(
            scenario=_scenario(jsonl_path),
            metrics=_metrics(),
            record_mapping={"run_id": "execution"},
        )


def test_jsonl_reader_rejects_empty_dataset(
    tmp_path: Path,
) -> None:
    """A JSONL file must contain at least one record."""
    jsonl_path = tmp_path / "empty.jsonl"

    jsonl_path.write_text(
        "\n   \n",
        encoding="utf-8",
    )

    with pytest.raises(
        DataValidationError,
        match="does not contain any data records",
    ):
        read_scenario(
            scenario=_scenario(jsonl_path),
            metrics=_metrics(),
            record_mapping={"run_id": "execution"},
        )