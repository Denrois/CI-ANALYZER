"""Tests for experiment data readers."""

from pathlib import Path

from ci_experiment_analyzer.models import (
    MetricConfig,
    ScenarioConfig,
    SourceConfig,
)
from ci_experiment_analyzer.readers import (
    read_csv_scenario,
    read_json_scenario,
    read_jsonl_scenario,
)


def _parallel_scenario(
    source_format: str,
    source_path: Path,
) -> ScenarioConfig:
    """Create a scenario containing parallel branch records."""
    return ScenarioConfig(
        id="baseline",
        source=SourceConfig(
            format=source_format,
            path=source_path,
        ),
    )


def _parallel_metrics() -> tuple[MetricConfig, ...]:
    """Create one parallel branch duration metric."""
    return (
        MetricConfig(
            id="branch_duration",
            field="branch_duration_seconds",
            metric_type="duration",
            unit="seconds",
            role="parallel_branch",
        ),
    )


def _parallel_record_mapping() -> dict[str, str]:
    """Create record mappings for parallel branch data."""
    return {
        "run_id": "workflow_run_id",
        "branch_id": "branch_id",
    }


def test_read_csv_scenario_uses_configured_field_names(
    tmp_path: Path,
) -> None:
    """CSV fields should be selected through metric configuration."""
    csv_path = tmp_path / "baseline.csv"

    csv_path.write_text(
        (
            "execution,dependency_time,total_time\n"
            "run-1,10.5,50.0\n"
            "run-2,12.5,54.0\n"
        ),
        encoding="utf-8",
    )

    scenario = ScenarioConfig(
        id="baseline",
        source=SourceConfig(
            format="csv",
            path=csv_path,
        ),
    )

    metrics = (
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

    dataset = read_csv_scenario(
        scenario=scenario,
        metrics=metrics,
        record_mapping={"run_id": "execution"},
    )

    assert dataset.scenario_id == "baseline"
    assert len(dataset.records) == 2

    assert dataset.records[0].run_id == "run-1"
    assert dataset.records[0].branch_id is None
    assert dataset.records[0].metric_values == {
        "install_duration": 10_500.0,
        "total_duration": 50_000.0,
    }

    assert dataset.records[1].run_id == "run-2"
    assert dataset.records[1].branch_id is None
    assert dataset.records[1].metric_values == {
        "install_duration": 12_500.0,
        "total_duration": 54_000.0,
    }


def test_read_csv_scenario_reads_parallel_branch_ids(
    tmp_path: Path,
) -> None:
    """CSV records should preserve run and branch identifiers."""
    csv_path = tmp_path / "parallel.csv"

    csv_path.write_text(
        (
            "workflow_run_id,branch_id,"
            "branch_duration_seconds\n"
            "run-1,shard-1,40.0\n"
            "run-1,shard-2,35.0\n"
            "run-2,shard-1,39.0\n"
        ),
        encoding="utf-8",
    )

    dataset = read_csv_scenario(
        scenario=_parallel_scenario(
            source_format="csv",
            source_path=csv_path,
        ),
        metrics=_parallel_metrics(),
        record_mapping=_parallel_record_mapping(),
    )

    assert [
        (
            record.run_id,
            record.branch_id,
            record.metric_values["branch_duration"],
        )
        for record in dataset.records
    ] == [
        ("run-1", "shard-1", 40_000.0),
        ("run-1", "shard-2", 35_000.0),
        ("run-2", "shard-1", 39_000.0),
    ]


def test_read_json_scenario_reads_parallel_branch_ids(
    tmp_path: Path,
) -> None:
    """JSON records should preserve run and branch identifiers."""
    json_path = tmp_path / "parallel.json"

    json_path.write_text(
        """
[
  {
    "workflow_run_id": "run-1",
    "branch_id": "shard-1",
    "branch_duration_seconds": 40.0
  },
  {
    "workflow_run_id": "run-1",
    "branch_id": "shard-2",
    "branch_duration_seconds": 35.0
  }
]
""".lstrip(),
        encoding="utf-8",
    )

    dataset = read_json_scenario(
        scenario=_parallel_scenario(
            source_format="json",
            source_path=json_path,
        ),
        metrics=_parallel_metrics(),
        record_mapping=_parallel_record_mapping(),
    )

    assert [
        (
            record.run_id,
            record.branch_id,
            record.metric_values["branch_duration"],
        )
        for record in dataset.records
    ] == [
        ("run-1", "shard-1", 40_000.0),
        ("run-1", "shard-2", 35_000.0),
    ]


def test_read_jsonl_scenario_reads_parallel_branch_ids(
    tmp_path: Path,
) -> None:
    """JSONL records should preserve run and branch identifiers."""
    jsonl_path = tmp_path / "parallel.jsonl"

    jsonl_path.write_text(
        (
            '{"workflow_run_id":"run-1",'
            '"branch_id":"shard-1",'
            '"branch_duration_seconds":40.0}\n'
            '{"workflow_run_id":"run-1",'
            '"branch_id":"shard-2",'
            '"branch_duration_seconds":35.0}\n'
        ),
        encoding="utf-8",
    )

    dataset = read_jsonl_scenario(
        scenario=_parallel_scenario(
            source_format="jsonl",
            source_path=jsonl_path,
        ),
        metrics=_parallel_metrics(),
        record_mapping=_parallel_record_mapping(),
    )

    assert [
        (
            record.run_id,
            record.branch_id,
            record.metric_values["branch_duration"],
        )
        for record in dataset.records
    ] == [
        ("run-1", "shard-1", 40_000.0),
        ("run-1", "shard-2", 35_000.0),
    ]