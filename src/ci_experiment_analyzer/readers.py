"""Read CI experiment records from input files."""

import csv
import math
from collections.abc import Mapping, Sequence
from pathlib import Path

from ci_experiment_analyzer.errors import DataValidationError
from ci_experiment_analyzer.models import (
    ExperimentConfig,
    MetricConfig,
    RunRecord,
    ScenarioConfig,
    ScenarioDataset,
)
from ci_experiment_analyzer.normalization import normalize_metric_value


def _require_value(
    row: Mapping[str, str | None],
    field: str,
    source_path: Path,
    line_number: int,
) -> str:
    """Return a required CSV value."""
    try:
        value = row[field]
    except KeyError as error:
        raise DataValidationError(
            f"CSV file {source_path} does not contain field {field!r}."
        ) from error

    if value is None or not value.strip():
        raise DataValidationError(
            f"CSV file {source_path}, line {line_number}, contains an "
            f"empty value for field {field!r}."
        )

    return value.strip()


def _validate_columns(
    fieldnames: Sequence[str] | None,
    run_id_field: str,
    metrics: Sequence[MetricConfig],
    source_path: Path,
) -> None:
    """Check that a CSV header contains every configured field."""
    if fieldnames is None:
        raise DataValidationError(
            f"CSV file {source_path} does not contain a header."
        )

    required_fields = {run_id_field}
    required_fields.update(metric.field for metric in metrics)

    missing_fields = sorted(required_fields.difference(fieldnames))

    if missing_fields:
        formatted_fields = ", ".join(repr(field) for field in missing_fields)

        raise DataValidationError(
            f"CSV file {source_path} is missing required field(s): "
            f"{formatted_fields}."
        )


def _parse_metric_value(
    row: Mapping[str, str | None],
    metric: MetricConfig,
    source_path: Path,
    line_number: int,
) -> float:
    """Read, validate, and normalize one metric value."""
    raw_value = _require_value(
        row=row,
        field=metric.field,
        source_path=source_path,
        line_number=line_number,
    )

    try:
        numeric_value = float(raw_value)
    except ValueError as error:
        raise DataValidationError(
            f"CSV file {source_path}, line {line_number}, field "
            f"{metric.field!r} contains non-numeric value "
            f"{raw_value!r}."
        ) from error

    if not math.isfinite(numeric_value):
        raise DataValidationError(
            f"CSV file {source_path}, line {line_number}, field "
            f"{metric.field!r} must contain a finite numeric value."
        )

    return normalize_metric_value(
        metric=metric,
        value=numeric_value,
    )


def read_csv_scenario(
    scenario: ScenarioConfig,
    metrics: Sequence[MetricConfig],
    record_mapping: Mapping[str, str],
) -> ScenarioDataset:
    """Read one scenario dataset from a CSV file."""
    source_path = scenario.source.path
    run_id_field = record_mapping["run_id"]
    records: list[RunRecord] = []

    with source_path.open(
        mode="r",
        encoding="utf-8-sig",
        newline="",
    ) as stream:
        reader = csv.DictReader(stream)

        _validate_columns(
            fieldnames=reader.fieldnames,
            run_id_field=run_id_field,
            metrics=metrics,
            source_path=source_path,
        )

        for row in reader:
            line_number = reader.line_num

            run_id = _require_value(
                row=row,
                field=run_id_field,
                source_path=source_path,
                line_number=line_number,
            )

            metric_values = {
                metric.id: _parse_metric_value(
                    row=row,
                    metric=metric,
                    source_path=source_path,
                    line_number=line_number,
                )
                for metric in metrics
            }

            records.append(
                RunRecord(
                    run_id=run_id,
                    metric_values=metric_values,
                )
            )

    if not records:
        raise DataValidationError(
            f"CSV file {source_path} does not contain any data records."
        )

    return ScenarioDataset(
        scenario_id=scenario.id,
        records=tuple(records),
    )


def read_scenario(
    scenario: ScenarioConfig,
    metrics: Sequence[MetricConfig],
    record_mapping: Mapping[str, str],
) -> ScenarioDataset:
    """Read one scenario using its configured source format."""
    if scenario.source.format != "csv":
        raise DataValidationError(
            f"Unsupported source format: {scenario.source.format!r}."
        )

    return read_csv_scenario(
        scenario=scenario,
        metrics=metrics,
        record_mapping=record_mapping,
    )


def read_experiment_datasets(
    config: ExperimentConfig,
) -> dict[str, ScenarioDataset]:
    """Read datasets for every scenario in an experiment."""
    return {
        scenario.id: read_scenario(
            scenario=scenario,
            metrics=config.metrics,
            record_mapping=config.record_mapping,
        )
        for scenario in config.scenarios
    }