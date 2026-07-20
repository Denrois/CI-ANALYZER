"""Tests for scenario data validation."""

from pathlib import Path

import pytest

from ci_experiment_analyzer.errors import DataValidationError
from ci_experiment_analyzer.models import (
    MetricConfig,
    ScenarioConfig,
    SourceConfig,
)
from ci_experiment_analyzer.readers import read_csv_scenario


def _scenario(csv_path: Path) -> ScenarioConfig:
    """Create a CSV scenario for a reader test."""
    return ScenarioConfig(
        id="baseline",
        source=SourceConfig(
            format="csv",
            path=csv_path,
        ),
    )


def _metrics() -> tuple[MetricConfig, ...]:
    """Create a duration metric for a reader test."""
    return (
        MetricConfig(
            id="duration",
            field="duration_seconds",
            metric_type="duration",
            unit="seconds",
            role="total",
        ),
    )


def test_reader_rejects_missing_metric_column(
    tmp_path: Path,
) -> None:
    """Every configured metric field must exist in the CSV header."""
    csv_path = tmp_path / "missing-column.csv"

    csv_path.write_text(
        "run_id,other_value\n"
        "run-1,10.0\n",
        encoding="utf-8",
    )

    with pytest.raises(
        DataValidationError,
        match="missing required field",
    ):
        read_csv_scenario(
            scenario=_scenario(csv_path),
            metrics=_metrics(),
            record_mapping={"run_id": "run_id"},
        )


def test_reader_rejects_non_numeric_metric_value(
    tmp_path: Path,
) -> None:
    """Metric values must be numeric."""
    csv_path = tmp_path / "non-numeric.csv"

    csv_path.write_text(
        "run_id,duration_seconds\n"
        "run-1,unknown\n",
        encoding="utf-8",
    )

    with pytest.raises(
        DataValidationError,
        match="contains non-numeric value",
    ):
        read_csv_scenario(
            scenario=_scenario(csv_path),
            metrics=_metrics(),
            record_mapping={"run_id": "run_id"},
        )


def test_reader_rejects_empty_run_id(
    tmp_path: Path,
) -> None:
    """Every experiment record must contain a run identifier."""
    csv_path = tmp_path / "empty-run-id.csv"

    csv_path.write_text(
        "run_id,duration_seconds\n"
        ",10.0\n",
        encoding="utf-8",
    )

    with pytest.raises(
        DataValidationError,
        match="empty value for field 'run_id'",
    ):
        read_csv_scenario(
            scenario=_scenario(csv_path),
            metrics=_metrics(),
            record_mapping={"run_id": "run_id"},
        )


def test_reader_rejects_non_finite_metric_value(
    tmp_path: Path,
) -> None:
    """Metric values such as NaN must not be accepted."""
    csv_path = tmp_path / "non-finite.csv"

    csv_path.write_text(
        "run_id,duration_seconds\n"
        "run-1,NaN\n",
        encoding="utf-8",
    )

    with pytest.raises(
        DataValidationError,
        match="must contain a finite numeric value",
    ):
        read_csv_scenario(
            scenario=_scenario(csv_path),
            metrics=_metrics(),
            record_mapping={"run_id": "run_id"},
        )


def test_reader_rejects_empty_dataset(
    tmp_path: Path,
) -> None:
    """A CSV file must contain at least one data record."""
    csv_path = tmp_path / "empty.csv"

    csv_path.write_text(
        "run_id,duration_seconds\n",
        encoding="utf-8",
    )

    with pytest.raises(
        DataValidationError,
        match="does not contain any data records",
    ):
        read_csv_scenario(
            scenario=_scenario(csv_path),
            metrics=_metrics(),
            record_mapping={"run_id": "run_id"},
        )


def test_reader_normalizes_seconds_to_milliseconds(
    tmp_path: Path,
) -> None:
    """Duration values should use milliseconds internally."""
    csv_path = tmp_path / "duration.csv"

    csv_path.write_text(
        "run_id,duration_seconds\n"
        "run-1,1.5\n",
        encoding="utf-8",
    )

    dataset = read_csv_scenario(
        scenario=_scenario(csv_path),
        metrics=_metrics(),
        record_mapping={"run_id": "run_id"},
    )

    assert len(dataset.records) == 1
    assert dataset.records[0].run_id == "run-1"
    assert (
        dataset.records[0].metric_values["duration"]
        == 1_500.0
    )