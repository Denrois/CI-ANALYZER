"""Read CI experiment records from input files."""

import csv
import json
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


def _parse_numeric_value(
    raw_value: object,
    metric: MetricConfig,
    source_path: Path,
    location: str,
) -> float:
    """Validate and normalize one numeric metric value."""
    if isinstance(raw_value, bool):
        raise DataValidationError(
            f"{location}, field {metric.field!r} contains non-numeric "
            f"value {raw_value!r}."
        )

    if isinstance(raw_value, str):
        value_text = raw_value.strip()

        if not value_text:
            raise DataValidationError(
                f"{location}, field {metric.field!r} contains an empty value."
            )

        try:
            numeric_value = float(value_text)
        except ValueError as error:
            raise DataValidationError(
                f"{location}, field {metric.field!r} contains non-numeric "
                f"value {raw_value!r}."
            ) from error

    elif isinstance(raw_value, (int, float)):
        numeric_value = float(raw_value)

    else:
        raise DataValidationError(
            f"{location}, field {metric.field!r} contains non-numeric "
            f"value {raw_value!r}."
        )

    if not math.isfinite(numeric_value):
        raise DataValidationError(
            f"{location}, field {metric.field!r} must contain a finite "
            "numeric value."
        )

    return normalize_metric_value(
        metric=metric,
        value=numeric_value,
    )


def _require_csv_value(
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


def _validate_csv_columns(
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
        formatted_fields = ", ".join(
            repr(field)
            for field in missing_fields
        )

        raise DataValidationError(
            f"CSV file {source_path} is missing required field(s): "
            f"{formatted_fields}."
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

    try:
        stream = source_path.open(
            mode="r",
            encoding="utf-8-sig",
            newline="",
        )
    except OSError as error:
        raise DataValidationError(
            f"Cannot read CSV file {source_path}: {error}"
        ) from error

    try:
        with stream:
            reader = csv.DictReader(stream)

            _validate_csv_columns(
                fieldnames=reader.fieldnames,
                run_id_field=run_id_field,
                metrics=metrics,
                source_path=source_path,
            )

            for row in reader:
                line_number = reader.line_num
                location = (
                    f"CSV file {source_path}, line {line_number}"
                )

                run_id = _require_csv_value(
                    row=row,
                    field=run_id_field,
                    source_path=source_path,
                    line_number=line_number,
                )

                metric_values = {
                    metric.id: _parse_numeric_value(
                        raw_value=_require_csv_value(
                            row=row,
                            field=metric.field,
                            source_path=source_path,
                            line_number=line_number,
                        ),
                        metric=metric,
                        source_path=source_path,
                        location=location,
                    )
                    for metric in metrics
                }

                records.append(
                    RunRecord(
                        run_id=run_id,
                        metric_values=metric_values,
                    )
                )
    except UnicodeError as error:
        raise DataValidationError(
            f"Cannot decode CSV file {source_path} as UTF-8."
        ) from error
    except csv.Error as error:
        raise DataValidationError(
            f"Cannot parse CSV file {source_path}: {error}"
        ) from error

    if not records:
        raise DataValidationError(
            f"CSV file {source_path} does not contain any data records."
        )

    return ScenarioDataset(
        scenario_id=scenario.id,
        records=tuple(records),
    )


def _load_json_document(source_path: Path) -> object:
    """Load one JSON document."""
    try:
        with source_path.open(
            mode="r",
            encoding="utf-8-sig",
        ) as stream:
            raw_data: object = json.load(stream)
    except json.JSONDecodeError as error:
        raise DataValidationError(
            f"Cannot parse JSON file {source_path}: "
            f"line {error.lineno}, column {error.colno}: {error.msg}."
        ) from error
    except UnicodeError as error:
        raise DataValidationError(
            f"Cannot decode JSON file {source_path} as UTF-8."
        ) from error
    except OSError as error:
        raise DataValidationError(
            f"Cannot read JSON file {source_path}: {error}"
        ) from error

    return raw_data


def _require_record(
    value: object,
    location: str,
) -> dict[str, object]:
    """Require one input record to be an object."""
    if not isinstance(value, dict):
        raise DataValidationError(
            f"{location} must be an object."
        )

    record: dict[str, object] = {}

    for key, item in value.items():
        if not isinstance(key, str):
            raise DataValidationError(
                f"{location} must contain only string field names."
            )

        record[key] = item

    return record


def _require_record_field(
    record: Mapping[str, object],
    field: str,
    location: str,
) -> object:
    """Return a required field from one structured record."""
    if field not in record:
        raise DataValidationError(
            f"{location} does not contain field {field!r}."
        )

    value = record[field]

    if value is None:
        raise DataValidationError(
            f"{location} contains an empty value for field {field!r}."
        )

    return value


def _parse_run_id(
    raw_value: object,
    field: str,
    location: str,
) -> str:
    """Validate and normalize one structured run identifier."""
    if isinstance(raw_value, str):
        run_id = raw_value.strip()

        if not run_id:
            raise DataValidationError(
                f"{location} contains an empty value for field {field!r}."
            )

        return run_id

    if isinstance(raw_value, bool):
        raise DataValidationError(
            f"{location} field {field!r} must contain a string or "
            "numeric identifier."
        )

    if isinstance(raw_value, int):
        return str(raw_value)

    if isinstance(raw_value, float):
        if not math.isfinite(raw_value):
            raise DataValidationError(
                f"{location} field {field!r} must contain a finite "
                "identifier."
            )

        return str(raw_value)

    raise DataValidationError(
        f"{location} field {field!r} must contain a string or "
        "numeric identifier."
    )


def read_json_scenario(
    scenario: ScenarioConfig,
    metrics: Sequence[MetricConfig],
    record_mapping: Mapping[str, str],
) -> ScenarioDataset:
    """Read one scenario dataset from a JSON array."""
    source_path = scenario.source.path
    run_id_field = record_mapping["run_id"]
    raw_data = _load_json_document(source_path)

    if not isinstance(raw_data, list):
        raise DataValidationError(
            f"JSON file {source_path} must contain a top-level list "
            "of records."
        )

    records: list[RunRecord] = []

    for record_number, raw_record in enumerate(
        raw_data,
        start=1,
    ):
        location = (
            f"JSON file {source_path}, record {record_number}"
        )

        record = _require_record(
            value=raw_record,
            location=location,
        )

        run_id = _parse_run_id(
            raw_value=_require_record_field(
                record=record,
                field=run_id_field,
                location=location,
            ),
            field=run_id_field,
            location=location,
        )

        metric_values = {
            metric.id: _parse_numeric_value(
                raw_value=_require_record_field(
                    record=record,
                    field=metric.field,
                    location=location,
                ),
                metric=metric,
                source_path=source_path,
                location=location,
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
            f"JSON file {source_path} does not contain any data records."
        )

    return ScenarioDataset(
        scenario_id=scenario.id,
        records=tuple(records),
    )


def read_jsonl_scenario(
    scenario: ScenarioConfig,
    metrics: Sequence[MetricConfig],
    record_mapping: Mapping[str, str],
) -> ScenarioDataset:
    """Read one scenario dataset from a JSONL file."""
    source_path = scenario.source.path
    run_id_field = record_mapping["run_id"]
    records: list[RunRecord] = []

    try:
        with source_path.open(
            mode="r",
            encoding="utf-8-sig",
        ) as stream:
            for line_number, raw_line in enumerate(
                stream,
                start=1,
            ):
                line = raw_line.strip()

                if not line:
                    continue

                location = (
                    f"JSONL file {source_path}, line {line_number}"
                )

                try:
                    raw_record: object = json.loads(line)
                except json.JSONDecodeError as error:
                    raise DataValidationError(
                        f"Cannot parse JSONL file {source_path}, "
                        f"line {line_number}, column {error.colno}: "
                        f"{error.msg}."
                    ) from error

                record = _require_record(
                    value=raw_record,
                    location=location,
                )

                run_id = _parse_run_id(
                    raw_value=_require_record_field(
                        record=record,
                        field=run_id_field,
                        location=location,
                    ),
                    field=run_id_field,
                    location=location,
                )

                metric_values = {
                    metric.id: _parse_numeric_value(
                        raw_value=_require_record_field(
                            record=record,
                            field=metric.field,
                            location=location,
                        ),
                        metric=metric,
                        source_path=source_path,
                        location=location,
                    )
                    for metric in metrics
                }

                records.append(
                    RunRecord(
                        run_id=run_id,
                        metric_values=metric_values,
                    )
                )

    except UnicodeError as error:
        raise DataValidationError(
            f"Cannot decode JSONL file {source_path} as UTF-8."
        ) from error
    except OSError as error:
        raise DataValidationError(
            f"Cannot read JSONL file {source_path}: {error}"
        ) from error

    if not records:
        raise DataValidationError(
            f"JSONL file {source_path} does not contain any data records."
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
    if scenario.source.format == "csv":
        return read_csv_scenario(
            scenario=scenario,
            metrics=metrics,
            record_mapping=record_mapping,
        )

    if scenario.source.format == "json":
        return read_json_scenario(
            scenario=scenario,
            metrics=metrics,
            record_mapping=record_mapping,
        )

    if scenario.source.format == "jsonl":
        return read_jsonl_scenario(
            scenario=scenario,
            metrics=metrics,
            record_mapping=record_mapping,
        )

    raise DataValidationError(
        f"Unsupported source format: {scenario.source.format!r}."
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