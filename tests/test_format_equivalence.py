"""Verify equivalent behavior across CSV, JSON, and JSONL inputs."""

import csv
import json
from collections.abc import Sequence
from pathlib import Path

from ci_experiment_analyzer.cli import main
from ci_experiment_analyzer.models import (
    MetricConfig,
    ScenarioConfig,
    SourceConfig,
)
from ci_experiment_analyzer.readers import read_scenario

Record = dict[str, object]


def _metrics() -> tuple[MetricConfig, ...]:
    """Create common metrics for format-equivalence tests."""
    return (
        MetricConfig(
            id="install_duration",
            field="install_seconds",
            metric_type="duration",
            unit="seconds",
            role="phase",
        ),
        MetricConfig(
            id="total_duration",
            field="total_seconds",
            metric_type="duration",
            unit="seconds",
            role="total",
        ),
    )


def _write_records(
    path: Path,
    source_format: str,
    records: Sequence[Record],
) -> None:
    """Write equivalent records in one supported source format."""
    if source_format == "csv":
        with path.open(
            mode="w",
            encoding="utf-8",
            newline="",
        ) as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=[
                    "run_id",
                    "install_seconds",
                    "total_seconds",
                ],
            )
            writer.writeheader()
            writer.writerows(records)

        return

    if source_format == "json":
        path.write_text(
            json.dumps(
                records,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return

    if source_format == "jsonl":
        path.write_text(
            "\n".join(
                json.dumps(record)
                for record in records
            )
            + "\n",
            encoding="utf-8",
        )
        return

    raise ValueError(f"Unsupported test format: {source_format!r}")


def _source_path(
    directory: Path,
    scenario_id: str,
    source_format: str,
) -> Path:
    """Build a source path for one scenario and format."""
    return directory / f"{scenario_id}.{source_format}"


def test_equivalent_sources_produce_equal_datasets(
    tmp_path: Path,
) -> None:
    """CSV, JSON, and JSONL should create equal scenario datasets."""
    records: list[Record] = [
        {
            "run_id": "run-1",
            "install_seconds": 10.5,
            "total_seconds": 50.0,
        },
        {
            "run_id": "run-2",
            "install_seconds": 12.5,
            "total_seconds": 54.0,
        },
    ]

    datasets = {}

    for source_format in ("csv", "json", "jsonl"):
        source_path = _source_path(
            directory=tmp_path,
            scenario_id="baseline",
            source_format=source_format,
        )

        _write_records(
            path=source_path,
            source_format=source_format,
            records=records,
        )

        scenario = ScenarioConfig(
            id="baseline",
            source=SourceConfig(
                format=source_format,
                path=source_path,
            ),
        )

        datasets[source_format] = read_scenario(
            scenario=scenario,
            metrics=_metrics(),
            record_mapping={"run_id": "run_id"},
        )

    assert datasets["json"] == datasets["csv"]
    assert datasets["jsonl"] == datasets["csv"]

    expected_records = datasets["csv"].records

    assert expected_records[0].run_id == "run-1"
    assert expected_records[0].metric_values == {
        "install_duration": 10_500.0,
        "total_duration": 50_000.0,
    }

    assert expected_records[1].run_id == "run-2"
    assert expected_records[1].metric_values == {
        "install_duration": 12_500.0,
        "total_duration": 54_000.0,
    }


def test_equivalent_sources_produce_equal_analysis_reports(
    tmp_path: Path,
) -> None:
    """The complete analysis result should be format-independent."""
    baseline_records: list[Record] = [
        {
            "run_id": "baseline-1",
            "install_seconds": 10.0,
            "total_seconds": 50.0,
        },
        {
            "run_id": "baseline-2",
            "install_seconds": 14.0,
            "total_seconds": 60.0,
        },
    ]

    optimized_records: list[Record] = [
        {
            "run_id": "optimized-1",
            "install_seconds": 8.0,
            "total_seconds": 45.0,
        },
        {
            "run_id": "optimized-2",
            "install_seconds": 10.0,
            "total_seconds": 51.0,
        },
    ]

    reports: dict[str, object] = {}

    for source_format in ("csv", "json", "jsonl"):
        experiment_directory = tmp_path / source_format
        data_directory = experiment_directory / "data"
        output_directory = experiment_directory / "report"

        data_directory.mkdir(parents=True)

        baseline_path = _source_path(
            directory=data_directory,
            scenario_id="baseline",
            source_format=source_format,
        )
        optimized_path = _source_path(
            directory=data_directory,
            scenario_id="optimized",
            source_format=source_format,
        )

        _write_records(
            path=baseline_path,
            source_format=source_format,
            records=baseline_records,
        )
        _write_records(
            path=optimized_path,
            source_format=source_format,
            records=optimized_records,
        )

        config_path = experiment_directory / "experiment.yaml"

        config_path.write_text(
            f"""
version: 1

experiment:
  id: format-equivalence-example
  title: Format equivalence example

scenarios:
  - id: baseline
    source:
      format: {source_format}
      path: data/{baseline_path.name}

  - id: optimized
    source:
      format: {source_format}
      path: data/{optimized_path.name}

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
  - id: optimization-impact
    baseline: baseline
    candidate: optimized
    metrics:
      - install_duration
      - total_duration
""".lstrip(),
            encoding="utf-8",
        )

        exit_code = main(
            [
                "analyze",
                "--config",
                str(config_path),
                "--output",
                str(output_directory),
            ]
        )

        assert exit_code == 0

        report_path = output_directory / "analysis.json"

        assert report_path.is_file()

        reports[source_format] = json.loads(
            report_path.read_text(encoding="utf-8")
        )

    assert reports["json"] == reports["csv"]
    assert reports["jsonl"] == reports["csv"]

    csv_report = reports["csv"]

    assert isinstance(csv_report, dict)

    comparison = csv_report["comparisons"][0]
    install_result = comparison["metrics"][0]
    total_result = comparison["metrics"][1]

    assert install_result == {
        "id": "install_duration",
        "unit": "milliseconds",
        "baseline_median": 12_000.0,
        "candidate_median": 9_000.0,
        "absolute_difference": -3_000.0,
        "relative_difference_percent": -25.0,
    }

    assert total_result == {
        "id": "total_duration",
        "unit": "milliseconds",
        "baseline_median": 55_000.0,
        "candidate_median": 48_000.0,
        "absolute_difference": -7_000.0,
        "relative_difference_percent": -12.727272727272727,
    }

    scenarios = csv_report["scenarios"]

    assert isinstance(scenarios, list)
    assert len(scenarios) == 2

    baseline_scenario = scenarios[0]

    assert baseline_scenario["id"] == "baseline"
    assert baseline_scenario["metrics"][0] == {
        "id": "install_duration",
        "unit": "milliseconds",
        "role": "phase",
        "count": 2,
        "median": 12_000.0,
        "mean": 12_000.0,
        "minimum": 10_000.0,
        "maximum": 14_000.0,
        "standard_deviation": 2_828.42712474619,
    }