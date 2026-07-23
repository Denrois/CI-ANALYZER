"""Tests for negative metric value handling."""

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


def _write_record(
    path: Path,
    source_format: str,
    value: float,
) -> None:
    """Write one equivalent record in a supported input format."""
    record = {
        "run_id": "run-1",
        "value": value,
    }

    if source_format == "csv":
        path.write_text(
            (
                "run_id,value\n"
                f"run-1,{value}\n"
            ),
            encoding="utf-8",
        )
        return

    if source_format == "json":
        path.write_text(
            json.dumps([record]) + "\n",
            encoding="utf-8",
        )
        return

    if source_format == "jsonl":
        path.write_text(
            json.dumps(record) + "\n",
            encoding="utf-8",
        )
        return

    raise AssertionError(
        f"Unsupported test format: {source_format!r}"
    )


def _read_metric_value(
    path: Path,
    source_format: str,
    metric_type: str,
) -> float:
    """Read one metric value using the configured reader."""
    scenario = ScenarioConfig(
        id="baseline",
        source=SourceConfig(
            format=source_format,
            path=path,
        ),
    )

    metric = MetricConfig(
        id="value",
        field="value",
        metric_type=metric_type,
        unit=(
            "seconds"
            if metric_type == "duration"
            else "count"
        ),
        role="total",
    )

    dataset = read_scenario(
        scenario=scenario,
        metrics=(metric,),
        record_mapping={"run_id": "run_id"},
    )

    return dataset.records[0].metric_values["value"]


@pytest.mark.parametrize(
    "source_format",
    (
        "csv",
        "json",
        "jsonl",
    ),
)
def test_readers_reject_negative_duration(
    tmp_path: Path,
    source_format: str,
) -> None:
    """Negative durations should be rejected in every input format."""
    source_path = tmp_path / f"negative.{source_format}"

    _write_record(
        path=source_path,
        source_format=source_format,
        value=-1.0,
    )

    with pytest.raises(
        DataValidationError,
        match="contains negative duration value -1.0",
    ):
        _read_metric_value(
            path=source_path,
            source_format=source_format,
            metric_type="duration",
        )


@pytest.mark.parametrize(
    "source_format",
    (
        "csv",
        "json",
        "jsonl",
    ),
)
def test_readers_accept_negative_number_metric(
    tmp_path: Path,
    source_format: str,
) -> None:
    """Generic numeric metrics may contain negative values."""
    source_path = tmp_path / f"negative-number.{source_format}"

    _write_record(
        path=source_path,
        source_format=source_format,
        value=-1.0,
    )

    result = _read_metric_value(
        path=source_path,
        source_format=source_format,
        metric_type="number",
    )

    assert result == -1.0