"""Validate experiment configuration."""
import math
from collections import Counter
from collections.abc import Sequence

from ci_experiment_analyzer.errors import ConfigValidationError
from ci_experiment_analyzer.models import ExperimentConfig

SUPPORTED_CONFIG_VERSIONS = frozenset({1})
SUPPORTED_SOURCE_FORMATS = frozenset(
    {
        "csv",
        "json",
        "jsonl",
    }
)
SUPPORTED_METRIC_TYPES = frozenset({"duration", "number"})
SUPPORTED_METRIC_ROLES = frozenset(
    {
        "phase",
        "total",
    }
)
SUPPORTED_DURATION_UNITS = frozenset(
    {
        "milliseconds",
        "seconds",
        "minutes",
    }
)


def _find_duplicates(values: Sequence[str]) -> tuple[str, ...]:
    """Return duplicate non-empty identifiers."""
    counts = Counter(values)

    return tuple(
        sorted(
            value
            for value, count in counts.items()
            if value and count > 1
        )
    )


def validate_config(config: ExperimentConfig) -> None:
    """Validate an experiment configuration.

    Raises:
        ConfigValidationError: If one or more configuration errors are found.
    """
    errors: list[str] = []

    if config.version not in SUPPORTED_CONFIG_VERSIONS:
        errors.append(
            f"unsupported configuration version {config.version!r}; "
            f"supported versions: {sorted(SUPPORTED_CONFIG_VERSIONS)}"
        )

    if not config.experiment.id.strip():
        errors.append("experiment id must not be empty")

    if not config.experiment.title.strip():
        errors.append("experiment title must not be empty")

    scenario_ids = tuple(scenario.id for scenario in config.scenarios)

    if not scenario_ids:
        errors.append("at least one scenario must be configured")

    for duplicate_id in _find_duplicates(scenario_ids):
        errors.append(f"duplicate scenario id: {duplicate_id!r}")

    for scenario in config.scenarios:
        if not scenario.id.strip():
            errors.append("scenario id must not be empty")

        if scenario.source.format not in SUPPORTED_SOURCE_FORMATS:
            errors.append(
                f"scenario {scenario.id!r} uses unsupported source format "
                f"{scenario.source.format!r}"
            )

        if not scenario.source.path.is_file():
            errors.append(
                f"source file for scenario {scenario.id!r} does not exist: "
                f"{scenario.source.path}"
            )

    run_id_field = config.record_mapping.get("run_id")

    if run_id_field is None or not run_id_field.strip():
        errors.append(
            "record_mapping must contain a non-empty 'run_id' field"
        )

    metric_ids = tuple(metric.id for metric in config.metrics)

    if not metric_ids:
        errors.append("at least one metric must be configured")

    for duplicate_id in _find_duplicates(metric_ids):
        errors.append(f"duplicate metric id: {duplicate_id!r}")

    for metric in config.metrics:
        if not metric.id.strip():
            errors.append("metric id must not be empty")

        if not metric.field.strip():
            errors.append(
                f"metric {metric.id!r} must define a non-empty source field"
            )

        if metric.metric_type not in SUPPORTED_METRIC_TYPES:
            errors.append(
                f"metric {metric.id!r} uses unsupported type "
                f"{metric.metric_type!r}"
            )

        if metric.role not in SUPPORTED_METRIC_ROLES:
            errors.append(
                f"metric {metric.id!r} uses unsupported role "
                f"{metric.role!r}; supported roles: "
                f"{sorted(SUPPORTED_METRIC_ROLES)}"
            )

        if (
            metric.metric_type == "duration"
            and metric.unit not in SUPPORTED_DURATION_UNITS
        ):
            errors.append(
                f"duration metric {metric.id!r} uses unsupported unit "
                f"{metric.unit!r}"
            )

    comparison_ids = tuple(
        comparison.id for comparison in config.comparisons
    )

    if not comparison_ids:
        errors.append("at least one comparison must be configured")

    for duplicate_id in _find_duplicates(comparison_ids):
        errors.append(f"duplicate comparison id: {duplicate_id!r}")

    scenario_id_set = set(scenario_ids)
    metric_id_set = set(metric_ids)

    for comparison in config.comparisons:
        if not comparison.id.strip():
            errors.append("comparison id must not be empty")

        if comparison.baseline not in scenario_id_set:
            errors.append(
                f"comparison {comparison.id!r} references unknown baseline "
                f"scenario {comparison.baseline!r}"
            )

        if comparison.candidate not in scenario_id_set:
            errors.append(
                f"comparison {comparison.id!r} references unknown candidate "
                f"scenario {comparison.candidate!r}"
            )

        if comparison.baseline == comparison.candidate:
            errors.append(
                f"comparison {comparison.id!r} must use different baseline "
                "and candidate scenarios"
            )

        if not comparison.metrics:
            errors.append(
                f"comparison {comparison.id!r} must reference at least "
                "one metric"
            )

        for metric_id in comparison.metrics:
            if metric_id not in metric_id_set:
                errors.append(
                    f"comparison {comparison.id!r} references unknown metric "
                    f"{metric_id!r}"
                )

    analysis_thresholds = {
        "local_improvement_threshold_pct": (
            config.analysis.local_improvement_threshold_pct
        ),
        "total_impact_threshold_pct": (
            config.analysis.total_impact_threshold_pct
        ),
    }

    for threshold_name, threshold_value in (
        analysis_thresholds.items()
    ):
        if not math.isfinite(threshold_value):
            errors.append(
                f"analysis threshold {threshold_name!r} "
                "must be finite"
            )
            continue

        if not 0.0 <= threshold_value <= 100.0:
            errors.append(
                f"analysis threshold {threshold_name!r} "
                "must be between 0 and 100"
            )

    if errors:
        raise ConfigValidationError(errors)