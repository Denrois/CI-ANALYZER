"""Load experiment configuration from YAML."""

from pathlib import Path
from typing import Any, cast

import yaml

from ci_experiment_analyzer.models import (
    ComparisonConfig,
    ExperimentConfig,
    ExperimentMetadata,
    MetricConfig,
    ScenarioConfig,
    SourceConfig,
)

RawMapping = dict[str, Any]


def _as_mapping(value: Any) -> RawMapping:
    """Treat a YAML value as a string-keyed mapping."""
    return cast(RawMapping, value)


def _as_mapping_list(value: Any) -> list[RawMapping]:
    """Treat a YAML value as a list of mappings."""
    return cast(list[RawMapping], value)


def _load_source(data: RawMapping, base_directory: Path) -> SourceConfig:
    """Create a source configuration and resolve its path."""
    source_path = Path(str(data["path"]))

    if not source_path.is_absolute():
        source_path = (base_directory / source_path).resolve()

    return SourceConfig(
        format=str(data["format"]),
        path=source_path,
    )


def _load_scenario(data: RawMapping, base_directory: Path) -> ScenarioConfig:
    """Create a scenario configuration."""
    return ScenarioConfig(
        id=str(data["id"]),
        source=_load_source(
            _as_mapping(data["source"]),
            base_directory,
        ),
    )


def _load_metric(data: RawMapping) -> MetricConfig:
    """Create a metric configuration."""
    return MetricConfig(
        id=str(data["id"]),
        field=str(data["field"]),
        metric_type=str(data["type"]),
        unit=str(data["unit"]),
        role=str(data["role"]),
    )


def _load_comparison(data: RawMapping) -> ComparisonConfig:
    """Create a comparison configuration."""
    metric_ids = cast(list[Any], data["metrics"])

    return ComparisonConfig(
        id=str(data["id"]),
        baseline=str(data["baseline"]),
        candidate=str(data["candidate"]),
        metrics=tuple(str(metric_id) for metric_id in metric_ids),
    )


def load_config(path: str | Path) -> ExperimentConfig:
    """Load an experiment configuration from a YAML file."""
    config_path = Path(path).resolve()

    with config_path.open(encoding="utf-8") as stream:
        raw_data: Any = yaml.safe_load(stream)

    data = _as_mapping(raw_data)
    experiment_data = _as_mapping(data["experiment"])
    record_mapping_data = _as_mapping(data["record_mapping"])

    scenarios = tuple(
        _load_scenario(item, config_path.parent)
        for item in _as_mapping_list(data["scenarios"])
    )

    metrics = tuple(
        _load_metric(item)
        for item in _as_mapping_list(data["metrics"])
    )

    comparisons = tuple(
        _load_comparison(item)
        for item in _as_mapping_list(data["comparisons"])
    )

    return ExperimentConfig(
        version=int(data["version"]),
        experiment=ExperimentMetadata(
            id=str(experiment_data["id"]),
            title=str(experiment_data["title"]),
        ),
        scenarios=scenarios,
        record_mapping={
            str(key): str(value)
            for key, value in record_mapping_data.items()
        },
        metrics=metrics,
        comparisons=comparisons,
    )