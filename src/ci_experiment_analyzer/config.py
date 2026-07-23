"""Load experiment configuration from YAML."""

from pathlib import Path
from typing import Any, cast

import yaml

from ci_experiment_analyzer.errors import ConfigLoadError
from ci_experiment_analyzer.models import (
    AnalysisConfig,
    ComparisonConfig,
    ExperimentConfig,
    ExperimentMetadata,
    MetricConfig,
    ScenarioConfig,
    SourceConfig,
)

RawMapping = dict[str, Any]


def _require_mapping(
    value: Any,
    context: str,
) -> RawMapping:
    """Require a YAML value to be a string-keyed mapping."""
    if not isinstance(value, dict):
        raise ConfigLoadError(
            f"{context} must be a mapping."
        )

    for key in value:
        if not isinstance(key, str):
            raise ConfigLoadError(
                f"{context} must contain only string keys."
            )

    return cast(RawMapping, value)


def _require_list(
    value: Any,
    context: str,
) -> list[Any]:
    """Require a YAML value to be a list."""
    if not isinstance(value, list):
        raise ConfigLoadError(
            f"{context} must be a list."
        )

    return  value


def _require_field(
    data: RawMapping,
    field: str,
    context: str,
) -> Any:
    """Return a required mapping field."""
    if field not in data:
        raise ConfigLoadError(
            f"{context} is missing required field {field!r}."
        )

    return data[field]


def _require_string(
    data: RawMapping,
    field: str,
    context: str,
) -> str:
    """Return a required string field."""
    value = _require_field(
        data=data,
        field=field,
        context=context,
    )

    if not isinstance(value, str):
        raise ConfigLoadError(
            f"{context} field {field!r} must be a string."
        )

    return value


def _require_integer(
    data: RawMapping,
    field: str,
    context: str,
) -> int:
    """Return a required integer field."""
    value = _require_field(
        data=data,
        field=field,
        context=context,
    )

    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigLoadError(
            f"{context} field {field!r} must be an integer."
        )

    return value


def _optional_number(
    data: RawMapping,
    field: str,
    context: str,
    default: float,
) -> float:
    """Return an optional integer or floating-point field."""
    if field not in data:
        return default

    value = data[field]

    if isinstance(value, bool) or not isinstance(
        value,
        (int, float),
    ):
        raise ConfigLoadError(
            f"{context} field {field!r} must be a number."
        )

    return float(value)


def _require_string_list(
    value: Any,
    context: str,
) -> tuple[str, ...]:
    """Require a YAML value to be a list of strings."""
    items = _require_list(value, context)
    result: list[str] = []

    for index, item in enumerate(items):
        if not isinstance(item, str):
            raise ConfigLoadError(
                f"{context}[{index}] must be a string."
            )

        result.append(item)

    return tuple(result)


def _load_source(
    value: Any,
    base_directory: Path,
    context: str,
) -> SourceConfig:
    """Create a source configuration."""
    data = _require_mapping(value, context)

    source_path = Path(
        _require_string(
            data=data,
            field="path",
            context=context,
        )
    )

    if not source_path.is_absolute():
        source_path = (
            base_directory / source_path
        ).resolve()

    return SourceConfig(
        format=_require_string(
            data=data,
            field="format",
            context=context,
        ),
        path=source_path,
    )


def _load_scenario(
    value: Any,
    base_directory: Path,
    index: int,
) -> ScenarioConfig:
    """Create a scenario configuration."""
    context = f"scenarios[{index}]"
    data = _require_mapping(value, context)

    return ScenarioConfig(
        id=_require_string(
            data=data,
            field="id",
            context=context,
        ),
        source=_load_source(
            value=_require_field(
                data=data,
                field="source",
                context=context,
            ),
            base_directory=base_directory,
            context=f"{context}.source",
        ),
    )


def _load_metric(
    value: Any,
    index: int,
) -> MetricConfig:
    """Create a metric configuration."""
    context = f"metrics[{index}]"
    data = _require_mapping(value, context)

    return MetricConfig(
        id=_require_string(
            data=data,
            field="id",
            context=context,
        ),
        field=_require_string(
            data=data,
            field="field",
            context=context,
        ),
        metric_type=_require_string(
            data=data,
            field="type",
            context=context,
        ),
        unit=_require_string(
            data=data,
            field="unit",
            context=context,
        ),
        role=_require_string(
            data=data,
            field="role",
            context=context,
        ),
    )


def _load_comparison(
    value: Any,
    index: int,
) -> ComparisonConfig:
    """Create a comparison configuration."""
    context = f"comparisons[{index}]"
    data = _require_mapping(value, context)

    return ComparisonConfig(
        id=_require_string(
            data=data,
            field="id",
            context=context,
        ),
        baseline=_require_string(
            data=data,
            field="baseline",
            context=context,
        ),
        candidate=_require_string(
            data=data,
            field="candidate",
            context=context,
        ),
        metrics=_require_string_list(
            value=_require_field(
                data=data,
                field="metrics",
                context=context,
            ),
            context=f"{context}.metrics",
        ),
    )


def _load_record_mapping(
    value: Any,
) -> dict[str, str]:
    """Load configured record field mappings."""
    data = _require_mapping(
        value,
        "record_mapping",
    )
    result: dict[str, str] = {}

    for key, mapped_field in data.items():
        if not isinstance(mapped_field, str):
            raise ConfigLoadError(
                f"record_mapping field {key!r} "
                "must map to a string value."
            )

        result[key] = mapped_field

    return result


def _load_analysis_config(
    value: Any,
) -> AnalysisConfig:
    """Load configurable higher-level analysis thresholds."""
    data = _require_mapping(
        value,
        "analysis",
    )

    defaults = AnalysisConfig()

    return AnalysisConfig(
        local_improvement_threshold_pct=_optional_number(
            data=data,
            field="local_improvement_threshold_pct",
            context="analysis",
            default=defaults.local_improvement_threshold_pct,
        ),
        total_impact_threshold_pct=_optional_number(
            data=data,
            field="total_impact_threshold_pct",
            context="analysis",
            default=defaults.total_impact_threshold_pct,
        ),
    )



def load_config(path: str | Path) -> ExperimentConfig:
    """Load an experiment configuration from a YAML file."""
    config_path = Path(path).resolve()

    try:
        raw_text = config_path.read_text(
            encoding="utf-8",
        )
    except OSError as error:
        raise ConfigLoadError(
            f"Cannot read configuration file "
            f"{config_path}: {error}"
        ) from error

    try:
        raw_data: Any = yaml.safe_load(raw_text)
    except yaml.YAMLError as error:
        raise ConfigLoadError(
            f"Cannot parse YAML configuration "
            f"{config_path}: {error}"
        ) from error

    data = _require_mapping(
        raw_data,
        "configuration root",
    )

    version = _require_integer(
        data=data,
        field="version",
        context="configuration root",
    )

    experiment_data = _require_mapping(
        _require_field(
            data=data,
            field="experiment",
            context="configuration root",
        ),
        "experiment",
    )

    scenario_items = _require_list(
        _require_field(
            data=data,
            field="scenarios",
            context="configuration root",
        ),
        "scenarios",
    )

    metric_items = _require_list(
        _require_field(
            data=data,
            field="metrics",
            context="configuration root",
        ),
        "metrics",
    )

    comparison_items = _require_list(
        _require_field(
            data=data,
            field="comparisons",
            context="configuration root",
        ),
        "comparisons",
    )

    record_mapping = _load_record_mapping(
        _require_field(
            data=data,
            field="record_mapping",
            context="configuration root",
        )
    )

    scenarios = tuple(
        _load_scenario(
            value=item,
            base_directory=config_path.parent,
            index=index,
        )
        for index, item in enumerate(scenario_items)
    )

    metrics = tuple(
        _load_metric(
            value=item,
            index=index,
        )
        for index, item in enumerate(metric_items)
    )

    comparisons = tuple(
        _load_comparison(
            value=item,
            index=index,
        )
        for index, item in enumerate(comparison_items)
    )

    if "analysis" in data:
        analysis = _load_analysis_config(
            data["analysis"]
        )
    else:
        analysis = AnalysisConfig()

    return ExperimentConfig(
        version=version,
        experiment=ExperimentMetadata(
            id=_require_string(
                data=experiment_data,
                field="id",
                context="experiment",
            ),
            title=_require_string(
                data=experiment_data,
                field="title",
                context="experiment",
            ),
        ),
        scenarios=scenarios,
        record_mapping=record_mapping,
        metrics=metrics,
        comparisons=comparisons,
        analysis=analysis,
    )