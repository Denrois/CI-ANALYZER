"""Read CI experiment records from input files."""

import csv
from collections.abc import Mapping, Sequence
from pathlib import Path

from ci_experiment_analyzer.models import (
    ExperimentConfig,
    MetricConfig,
    RunRecord,
    ScenarioConfig,
    ScenarioDataset,
)


def _require_value(
    row: Mapping[str, str | None],
    field: str,
    source_path: Path,
) -> str:
    """Return a required CSV value."""
    try:
        value = row[field]
    except KeyError as error:
        raise ValueError(
            f"CSV file {source_path} does not contain field {field!r}."
        ) from error

    if value is None or not value.strip():
        raise ValueError(
            f"CSV file {source_path} contains an empty value "
            f"for field {field!r}."
        )

    return value


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

        for row in reader:
            run_id = _require_value(
                row=row,
                field=run_id_field,
                source_path=source_path,
            )

            metric_values = {
                metric.id: float(
                    _require_value(
                        row=row,
                        field=metric.field,
                        source_path=source_path,
                    )
                )
                for metric in metrics
            }

            records.append(
                RunRecord(
                    run_id=run_id,
                    metric_values=metric_values,
                )
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
        raise ValueError(
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