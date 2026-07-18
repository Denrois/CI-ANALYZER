"""Tests for experiment data readers."""

from pathlib import Path

from ci_experiment_analyzer.models import (
    MetricConfig,
    ScenarioConfig,
    SourceConfig,
)
from ci_experiment_analyzer.readers import read_csv_scenario


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
    assert dataset.records[0].metric_values == {
        "install_duration": 10.5,
        "total_duration": 50.0,
    }

    assert dataset.records[1].run_id == "run-2"
    assert dataset.records[1].metric_values == {
        "install_duration": 12.5,
        "total_duration": 54.0,
    }