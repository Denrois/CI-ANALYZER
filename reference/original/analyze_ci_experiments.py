from __future__ import annotations

import argparse
import csv
import json
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Scenario:
    name: str
    group: str
    role: str
    description: str


@dataclass(frozen=True)
class MetricStats:
    count: int
    median: float
    mean: float
    minimum: float
    maximum: float
    stdev: float


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        name="dependency_baseline",
        group="dependency_cache",
        role="baseline",
        description="Backend CI run without dependency cache.",
    ),
    Scenario(
        name="dependency_cache",
        group="dependency_cache",
        role="optimized",
        description="Backend CI run with warm dependency cache.",
    ),
    Scenario(
        name="docker_baseline",
        group="docker_build_cache",
        role="baseline",
        description="Docker/Compose run without Docker build cache.",
    ),
    Scenario(
        name="docker_cache_fixed",
        group="docker_build_cache",
        role="optimized",
        description="Corrected Docker build cache run.",
    ),
    Scenario(
        name="docker_cache_first",
        group="docker_build_cache",
        role="diagnostic",
        description="First Docker cache variant used for diagnostics.",
    ),
    Scenario(
        name="docker_cache_cold",
        group="docker_build_cache",
        role="diagnostic",
        description="Cold-cache initialization run.",
    ),
    Scenario(
        name="sharding_baseline_original",
        group="sharding_original",
        role="baseline",
        description="Baseline sharding on the original test suite.",
    ),
    Scenario(
        name="sharding_timing_original",
        group="sharding_original",
        role="optimized",
        description="Timing-based sharding on the original test suite.",
    ),
    Scenario(
        name="sharding_baseline_extended",
        group="sharding_extended",
        role="baseline",
        description="Baseline sharding on the extended test suite.",
    ),
    Scenario(
        name="sharding_timing_extended",
        group="sharding_extended",
        role="optimized",
        description="Timing-based sharding on the extended test suite.",
    ),
)

@dataclass(frozen=True)
class MetricComparison:
    metric_name: str
    baseline_median: float
    optimized_median: float
    difference: float
    relative_change_pct: float


NUMERIC_METRICS: tuple[str, ...] = (
    "dependency_prepare_duration_ms",
    "services_start_duration_ms",
    "migration_duration_ms",
    "test_duration_ms",
    "measured_total_duration_ms",
    "docker_build_duration_ms",
    "backend_healthcheck_duration_ms",
    "frontend_healthcheck_duration_ms",
    "shard_duration_ms",
)

SECONDS_TO_MS_FIELDS: dict[str, str] = {
    "setup_duration_seconds": "setup_duration_ms",
    "dependency_prepare_duration_seconds": "dependency_prepare_duration_ms",
    "services_start_duration_seconds": "services_start_duration_ms",
    "migration_duration_seconds": "migration_duration_ms",
    "test_duration_seconds": "test_duration_ms",
    "docker_build_duration_seconds": "docker_build_duration_ms",
    "backend_healthcheck_duration_seconds": "backend_healthcheck_duration_ms",
    "frontend_healthcheck_duration_seconds": "frontend_healthcheck_duration_ms",
    "measured_total_duration_seconds": "measured_total_duration_ms",
    "shard_duration_seconds": "shard_duration_ms",
}

BOTTLENECK_METRICS: tuple[str, ...] = (
    "dependency_prepare_duration_ms",
    "services_start_duration_ms",
    "migration_duration_ms",
    "test_duration_ms",
    "docker_build_duration_ms",
    "backend_healthcheck_duration_ms",
    "frontend_healthcheck_duration_ms",
    "measured_total_duration_ms",
)

COMPARISON_PAIRS: tuple[tuple[str, str, str], ...] = (
    ("dependency_cache", "dependency_baseline", "dependency_cache"),
    ("docker_build_cache", "docker_baseline", "docker_cache_fixed"),
    ("sharding_original", "sharding_baseline_original", "sharding_timing_original"),
    ("sharding_extended", "sharding_baseline_extended", "sharding_timing_extended"),
)

SHARDING_SCENARIO_NAMES: tuple[str, ...] = (
    "sharding_baseline_original",
    "sharding_timing_original",
    "sharding_baseline_extended",
    "sharding_timing_extended",
)

@dataclass(frozen=True)
class ShardingRunMetrics:
    run_id: str
    shard_count: int
    critical_path_ms: float
    average_shard_ms: float
    fastest_shard_ms: float
    slowest_shard_ms: float
    spread_ms: float
    imbalance_ratio: float


@dataclass(frozen=True)
class ShardingMetricComparison:
    group_name: str
    metric_name: str
    baseline_median: float
    optimized_median: float
    difference: float
    relative_change_pct: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze CI experiment metrics exported from GitHub Actions "
            "for the FastAPI thesis project."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("analysis/input"),
        help="Directory with input metric files grouped by experiment scenario.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("analysis/output"),
        help="Directory where analysis outputs will be written.",
    )
    parser.add_argument(
        "--allow-missing-scenarios",
        action="store_true",
        help="Allow missing scenario directories, useful for sample input data.",
    )
    return parser.parse_args()


def get_metric_files(scenario_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in scenario_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".json", ".jsonl"}
    )


def parse_json_text(text: str, source: Path) -> list[dict[str, Any]]:
    stripped = text.strip()
    if not stripped:
        return []

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return parse_json_lines_or_concatenated(stripped, source)

    if isinstance(parsed, dict):
        return [parsed]

    if isinstance(parsed, list):
        records: list[dict[str, Any]] = []
        for index, item in enumerate(parsed):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Expected JSON object in list at index {index} in {source}"
                )
            records.append(item)
        return records

    raise ValueError(f"Expected JSON object or list in {source}")


def parse_json_lines_or_concatenated(text: str, source: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    jsonl_records: list[dict[str, Any]] = []
    jsonl_failed = False

    for line_number, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue

        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            jsonl_failed = True
            break

        if not isinstance(parsed, dict):
            raise ValueError(
                f"Expected JSON object on line {line_number} in {source}"
            )

        jsonl_records.append(parsed)

    if not jsonl_failed:
        return jsonl_records

    decoder = json.JSONDecoder()
    position = 0

    while position < len(text):
        while position < len(text) and text[position].isspace():
            position += 1

        if position >= len(text):
            break

        try:
            parsed, next_position = decoder.raw_decode(text, position)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Could not parse JSON content in {source}: {exc}") from exc

        if not isinstance(parsed, dict):
            raise ValueError(f"Expected concatenated JSON object in {source}")

        records.append(parsed)
        position = next_position

    return records


def load_metric_records(scenario_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for metric_file in get_metric_files(scenario_dir):
        text = metric_file.read_text(encoding="utf-8")
        parsed_records = parse_json_text(text, metric_file)
        records.extend(
            normalize_time_units(record)
            for record in parsed_records
        )

    return records


def validate_input_structure(
    input_dir: Path,
    *,
    allow_missing_scenarios: bool,
) -> list[str]:
    errors: list[str] = []

    if not input_dir.exists():
        errors.append(f"Input directory does not exist: {input_dir}")
        return errors

    for scenario in SCENARIOS:
        scenario_dir = input_dir / scenario.name
        if not scenario_dir.exists():
            if not allow_missing_scenarios:
                errors.append(f"Missing scenario directory: {scenario_dir}")
        elif not scenario_dir.is_dir():
            errors.append(f"Scenario path is not a directory: {scenario_dir}")

    return errors


def as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None

    if isinstance(value, int | float):
        return float(value)

    if isinstance(value, str):
        normalized = value.strip().replace(",", ".")
        if not normalized:
            return None
        try:
            return float(normalized)
        except ValueError:
            return None

    return None

def normalize_time_units(record: dict[str, Any]) -> dict[str, Any]:
    """Normalize duration metrics to milliseconds.

    Raw metric files may contain duration values either in milliseconds
    or in seconds. The analyzer uses milliseconds internally. Original
    fields are preserved and *_ms aliases are added when only *_seconds
    values are available.
    """
    normalized = dict(record)

    for seconds_key, ms_key in SECONDS_TO_MS_FIELDS.items():
        if ms_key in normalized:
            continue

        if seconds_key not in normalized:
            continue

        value = as_float(normalized[seconds_key])
        if value is None:
            continue

        normalized[ms_key] = value * 1000

    return normalized

def collect_metric_values(
    records: list[dict[str, Any]],
    metric_name: str,
) -> list[float]:
    values: list[float] = []

    for record in records:
        if metric_name not in record:
            continue

        value = as_float(record[metric_name])
        if value is not None:
            values.append(value)

    return values


def compute_metric_stats(values: list[float]) -> MetricStats | None:
    if not values:
        return None

    return MetricStats(
        count=len(values),
        median=statistics.median(values),
        mean=statistics.mean(values),
        minimum=min(values),
        maximum=max(values),
        stdev=statistics.stdev(values) if len(values) > 1 else 0.0,
    )


def compute_scenario_stats(
    records_by_scenario: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, MetricStats]]:
    result: dict[str, dict[str, MetricStats]] = {}

    for scenario_name, records in records_by_scenario.items():
        metric_stats: dict[str, MetricStats] = {}

        for metric_name in NUMERIC_METRICS:
            values = collect_metric_values(records, metric_name)
            stats = compute_metric_stats(values)
            if stats is not None:
                metric_stats[metric_name] = stats

        result[scenario_name] = metric_stats

    return result


def compare_metric_stats(
    metric_name: str,
    baseline_stats: MetricStats,
    optimized_stats: MetricStats,
) -> MetricComparison:
    difference = optimized_stats.median - baseline_stats.median

    if baseline_stats.median == 0:
        relative_change_pct = 0.0
    else:
        relative_change_pct = difference / baseline_stats.median * 100

    return MetricComparison(
        metric_name=metric_name,
        baseline_median=baseline_stats.median,
        optimized_median=optimized_stats.median,
        difference=difference,
        relative_change_pct=relative_change_pct,
    )


def compute_comparisons(
    stats_by_scenario: dict[str, dict[str, MetricStats]],
) -> dict[str, list[MetricComparison]]:
    comparisons: dict[str, list[MetricComparison]] = {}

    for group_name, baseline_name, optimized_name in COMPARISON_PAIRS:
        baseline_metrics = stats_by_scenario.get(baseline_name, {})
        optimized_metrics = stats_by_scenario.get(optimized_name, {})

        if not baseline_metrics or not optimized_metrics:
            continue

        group_comparisons: list[MetricComparison] = []

        for metric_name in NUMERIC_METRICS:
            baseline_stats = baseline_metrics.get(metric_name)
            optimized_stats = optimized_metrics.get(metric_name)

            if baseline_stats is None or optimized_stats is None:
                continue

            group_comparisons.append(
                compare_metric_stats(
                    metric_name=metric_name,
                    baseline_stats=baseline_stats,
                    optimized_stats=optimized_stats,
                )
            )

        comparisons[group_name] = group_comparisons

    return comparisons


def compute_sharding_run_metrics(
    records_by_scenario: dict[str, list[dict[str, Any]]],
) -> dict[str, list[ShardingRunMetrics]]:
    result: dict[str, list[ShardingRunMetrics]] = {}

    for scenario_name in SHARDING_SCENARIO_NAMES:
        records = records_by_scenario.get(scenario_name, [])
        shards_by_run: dict[str, list[float]] = {}

        for record in records:
            duration = as_float(record.get("shard_duration_ms"))
            if duration is None:
                continue

            run_id_value = (
                record.get("run_id")
                or record.get("github_run_id")
                or record.get("run_number")
                or "unknown_run"
            )
            run_id = str(run_id_value)

            shards_by_run.setdefault(run_id, []).append(duration)

        scenario_metrics: list[ShardingRunMetrics] = []

        for run_id in sorted(shards_by_run):
            durations = shards_by_run[run_id]
            if not durations:
                continue

            average_shard_ms = statistics.mean(durations)
            fastest_shard_ms = min(durations)
            slowest_shard_ms = max(durations)
            spread_ms = slowest_shard_ms - fastest_shard_ms
            imbalance_ratio = (
                slowest_shard_ms / average_shard_ms
                if average_shard_ms > 0
                else 0.0
            )

            scenario_metrics.append(
                ShardingRunMetrics(
                    run_id=run_id,
                    shard_count=len(durations),
                    critical_path_ms=slowest_shard_ms,
                    average_shard_ms=average_shard_ms,
                    fastest_shard_ms=fastest_shard_ms,
                    slowest_shard_ms=slowest_shard_ms,
                    spread_ms=spread_ms,
                    imbalance_ratio=imbalance_ratio,
                )
            )

        if scenario_metrics:
            result[scenario_name] = scenario_metrics

    return result


def summarize_sharding_run_metrics(
    run_metrics: list[ShardingRunMetrics],
) -> dict[str, MetricStats]:
    metric_values = {
        "critical_path_ms": [metric.critical_path_ms for metric in run_metrics],
        "average_shard_ms": [metric.average_shard_ms for metric in run_metrics],
        "spread_ms": [metric.spread_ms for metric in run_metrics],
        "imbalance_ratio": [metric.imbalance_ratio for metric in run_metrics],
    }

    summary: dict[str, MetricStats] = {}

    for metric_name, values in metric_values.items():
        stats = compute_metric_stats(values)
        if stats is not None:
            summary[metric_name] = stats

    return summary


def compare_sharding_metric_stats(
    group_name: str,
    metric_name: str,
    baseline_stats: MetricStats,
    optimized_stats: MetricStats,
) -> ShardingMetricComparison:
    difference = optimized_stats.median - baseline_stats.median

    if baseline_stats.median == 0:
        relative_change_pct = 0.0
    else:
        relative_change_pct = difference / baseline_stats.median * 100

    return ShardingMetricComparison(
        group_name=group_name,
        metric_name=metric_name,
        baseline_median=baseline_stats.median,
        optimized_median=optimized_stats.median,
        difference=difference,
        relative_change_pct=relative_change_pct,
    )


def compute_sharding_comparisons(
    sharding_run_metrics: dict[str, list[ShardingRunMetrics]],
) -> dict[str, list[ShardingMetricComparison]]:
    comparison_pairs = (
        (
            "sharding_original",
            "sharding_baseline_original",
            "sharding_timing_original",
        ),
        (
            "sharding_extended",
            "sharding_baseline_extended",
            "sharding_timing_extended",
        ),
    )

    compared_metrics = (
        "critical_path_ms",
        "spread_ms",
        "imbalance_ratio",
    )

    result: dict[str, list[ShardingMetricComparison]] = {}

    for group_name, baseline_name, optimized_name in comparison_pairs:
        baseline_runs = sharding_run_metrics.get(baseline_name)
        optimized_runs = sharding_run_metrics.get(optimized_name)

        if not baseline_runs or not optimized_runs:
            continue

        baseline_summary = summarize_sharding_run_metrics(baseline_runs)
        optimized_summary = summarize_sharding_run_metrics(optimized_runs)

        group_result: list[ShardingMetricComparison] = []

        for metric_name in compared_metrics:
            baseline_stats = baseline_summary.get(metric_name)
            optimized_stats = optimized_summary.get(metric_name)

            if baseline_stats is None or optimized_stats is None:
                continue

            group_result.append(
                compare_sharding_metric_stats(
                    group_name=group_name,
                    metric_name=metric_name,
                    baseline_stats=baseline_stats,
                    optimized_stats=optimized_stats,
                )
            )

        if group_result:
            result[group_name] = group_result

    return result


def detect_bottlenecks(
    stats_by_scenario: dict[str, dict[str, MetricStats]],
) -> dict[str, tuple[str, MetricStats]]:
    bottlenecks: dict[str, tuple[str, MetricStats]] = {}

    excluded_metrics = {"measured_total_duration_ms", "shard_duration_ms"}

    for scenario_name, scenario_stats in stats_by_scenario.items():
        candidates: list[tuple[str, MetricStats]] = []

        for metric_name, metric_stats in scenario_stats.items():
            if metric_name in excluded_metrics:
                continue
            if metric_name not in BOTTLENECK_METRICS:
                continue

            candidates.append((metric_name, metric_stats))

        if not candidates:
            continue

        bottlenecks[scenario_name] = max(
            candidates,
            key=lambda item: item[1].median,
        )

    return bottlenecks


def format_ms(value: float) -> str:
    return f"{value / 1000:.3f} s"


def seconds(value_ms: float) -> float:
    return round(value_ms / 1000, 6)


def format_pct(value: float) -> str:
    return f"{value:.1f} %"


def format_ratio(value: float) -> str:
    return f"{value:.3f}"


def format_metric_summary_value(metric_name: str, value: float) -> str:
    if metric_name == "imbalance_ratio":
        return format_ratio(value)
    return f"{seconds(value):.3f}"


def humanize_metric_name(metric_name: str) -> str:
    names = {
        "dependency_prepare_duration_ms": "Dependency preparation",
        "services_start_duration_ms": "Services start",
        "migration_duration_ms": "Database migrations",
        "test_duration_ms": "Tests",
        "measured_total_duration_ms": "Measured total",
        "docker_build_duration_ms": "Docker build",
        "backend_healthcheck_duration_ms": "Backend healthcheck",
        "frontend_healthcheck_duration_ms": "Frontend healthcheck",
        "shard_duration_ms": "Shard duration",
        "critical_path_ms": "Critical path",
        "average_shard_ms": "Average shard duration",
        "fastest_shard_ms": "Fastest shard",
        "slowest_shard_ms": "Slowest shard",
        "spread_ms": "Shard spread",
        "imbalance_ratio": "Imbalance ratio",
    }
    return names.get(metric_name, metric_name)


def print_scenario_overview(input_dir: Path) -> dict[str, list[dict[str, Any]]]:
    loaded_records: dict[str, list[dict[str, Any]]] = {}

    print("Configured scenarios:")
    for scenario in SCENARIOS:
        scenario_dir = input_dir / scenario.name
        exists = scenario_dir.exists() and scenario_dir.is_dir()

        if exists:
            metric_files = get_metric_files(scenario_dir)
            records = load_metric_records(scenario_dir)
        else:
            metric_files = []
            records = []

        loaded_records[scenario.name] = records

        status = "OK" if exists else "MISSING"
        print(
            f"- {scenario.name} "
            f"[{scenario.group}, {scenario.role}] "
            f"{status}, files={len(metric_files)}, records={len(records)}"
        )

    return loaded_records


def print_stats_summary(
    stats_by_scenario: dict[str, dict[str, MetricStats]],
) -> None:
    print()
    print("Metric statistics:")

    any_stats = False

    for scenario in SCENARIOS:
        scenario_stats = stats_by_scenario.get(scenario.name, {})
        if not scenario_stats:
            continue

        any_stats = True
        print(f"\n{scenario.name}:")

        for metric_name, stats in scenario_stats.items():
            print(
                f"- {metric_name}: "
                f"count={stats.count}, "
                f"median={format_ms(stats.median)}, "
                f"mean={format_ms(stats.mean)}, "
                f"min={format_ms(stats.minimum)}, "
                f"max={format_ms(stats.maximum)}, "
                f"stdev={format_ms(stats.stdev)}"
            )

    if not any_stats:
        print("- No numeric metrics found yet.")


def print_comparison_summary(
    comparisons: dict[str, list[MetricComparison]],
) -> None:
    print()
    print("Baseline vs optimized comparisons:")

    if not comparisons:
        print("- No comparison pairs available yet.")
        return

    for group_name, group_comparisons in comparisons.items():
        if not group_comparisons:
            continue

        print(f"\n{group_name}:")
        for comparison in group_comparisons:
            print(
                f"- {comparison.metric_name}: "
                f"baseline={format_ms(comparison.baseline_median)}, "
                f"optimized={format_ms(comparison.optimized_median)}, "
                f"difference={format_ms(comparison.difference)}, "
                f"relative_change={comparison.relative_change_pct:.1f} %"
            )


def sharding_run_metric_to_dict(
    metric: ShardingRunMetrics,
) -> dict[str, float | int | str]:
    return {
        "run_id": metric.run_id,
        "shard_count": metric.shard_count,
        "critical_path_ms": metric.critical_path_ms,
        "average_shard_ms": metric.average_shard_ms,
        "fastest_shard_ms": metric.fastest_shard_ms,
        "slowest_shard_ms": metric.slowest_shard_ms,
        "spread_ms": metric.spread_ms,
        "critical_path_seconds": metric.critical_path_ms / 1000,
        "average_shard_seconds": metric.average_shard_ms / 1000,
        "fastest_shard_seconds": metric.fastest_shard_ms / 1000,
        "slowest_shard_seconds": metric.slowest_shard_ms / 1000,
        "spread_seconds": metric.spread_ms / 1000,
        "imbalance_ratio": metric.imbalance_ratio,
    }


def build_sharding_metrics_payload(
    sharding_run_metrics: dict[str, list[ShardingRunMetrics]],
) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    for scenario_name, run_metrics in sharding_run_metrics.items():
        summary = summarize_sharding_run_metrics(run_metrics)

        payload[scenario_name] = {
            "runs": [
                sharding_run_metric_to_dict(metric)
                for metric in run_metrics
            ],
            "summary": {
                metric_name: metric_stats_to_payload(metric_name, metric_stats)
                for metric_name, metric_stats in summary.items()
            },
        }

    return payload


def metric_stats_to_dict(stats: MetricStats) -> dict[str, float | int]:
    return {
        "count": stats.count,
        "median_ms": stats.median,
        "mean_ms": stats.mean,
        "min_ms": stats.minimum,
        "max_ms": stats.maximum,
        "stdev_ms": stats.stdev,
        "median_seconds": stats.median / 1000,
        "mean_seconds": stats.mean / 1000,
        "min_seconds": stats.minimum / 1000,
        "max_seconds": stats.maximum / 1000,
        "stdev_seconds": stats.stdev / 1000,
    }


def metric_stats_to_value_dict(stats: MetricStats) -> dict[str, float | int]:
    return {
        "count": stats.count,
        "median": stats.median,
        "mean": stats.mean,
        "min": stats.minimum,
        "max": stats.maximum,
        "stdev": stats.stdev,
    }


def metric_stats_to_payload(
    metric_name: str,
    stats: MetricStats,
) -> dict[str, float | int]:
    if metric_name == "imbalance_ratio":
        return metric_stats_to_value_dict(stats)

    return metric_stats_to_dict(stats)


def comparison_to_dict(comparison: MetricComparison) -> dict[str, float | str]:
    return {
        "metric_name": comparison.metric_name,
        "baseline_median_ms": comparison.baseline_median,
        "optimized_median_ms": comparison.optimized_median,
        "difference_ms": comparison.difference,
        "relative_change_pct": comparison.relative_change_pct,
        "baseline_median_seconds": comparison.baseline_median / 1000,
        "optimized_median_seconds": comparison.optimized_median / 1000,
        "difference_seconds": comparison.difference / 1000,
    }


def sharding_comparison_to_dict(
    comparison: ShardingMetricComparison,
) -> dict[str, float | str]:
    result: dict[str, float | str] = {
        "group_name": comparison.group_name,
        "metric_name": comparison.metric_name,
        "baseline_median": comparison.baseline_median,
        "optimized_median": comparison.optimized_median,
        "difference": comparison.difference,
        "relative_change_pct": comparison.relative_change_pct,
    }

    if comparison.metric_name != "imbalance_ratio":
        result.update(
            {
                "baseline_median_seconds": comparison.baseline_median / 1000,
                "optimized_median_seconds": comparison.optimized_median / 1000,
                "difference_seconds": comparison.difference / 1000,
            }
        )

    return result


def build_computed_metrics_payload(
    records_by_scenario: dict[str, list[dict[str, Any]]],
    stats_by_scenario: dict[str, dict[str, MetricStats]],
    comparisons: dict[str, list[MetricComparison]],
    bottlenecks: dict[str, tuple[str, MetricStats]],
    sharding_run_metrics: dict[str, list[ShardingRunMetrics]],
    sharding_comparisons: dict[str, list[ShardingMetricComparison]],
) -> dict[str, Any]:
    return {
        "metadata": {
            "tool": "analyze_ci_experiments.py",
            "scope": "FastAPI thesis CI experiment metrics",
            "total_loaded_records": sum(
                len(records) for records in records_by_scenario.values()
            ),
            "scenarios": [asdict(scenario) for scenario in SCENARIOS],
        },
        "scenario_statistics": {
            scenario_name: {
                metric_name: metric_stats_to_dict(metric_stats)
                for metric_name, metric_stats in scenario_stats.items()
            }
            for scenario_name, scenario_stats in stats_by_scenario.items()
        },
        "comparisons": {
            group_name: [
                comparison_to_dict(comparison)
                for comparison in group_comparisons
            ]
            for group_name, group_comparisons in comparisons.items()
        },
        "bottlenecks": {
            scenario_name: {
                "metric_name": metric_name,
                "metric_label": humanize_metric_name(metric_name),
                **metric_stats_to_dict(metric_stats),
            }
            for scenario_name, (metric_name, metric_stats) in bottlenecks.items()
        },
        "sharding_run_metrics": build_sharding_metrics_payload(
            sharding_run_metrics
        ),
        "sharding_comparisons": {
            group_name: [
                sharding_comparison_to_dict(comparison)
                for comparison in group_comparisons
            ]
            for group_name, group_comparisons in sharding_comparisons.items()
        },
    }


def write_computed_metrics_json(
    output_dir: Path,
    payload: dict[str, Any],
) -> Path:
    output_path = output_dir / "computed_metrics.json"
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path


def write_summary_tables_csv(
    output_dir: Path,
    stats_by_scenario: dict[str, dict[str, MetricStats]],
    comparisons: dict[str, list[MetricComparison]],
    bottlenecks: dict[str, tuple[str, MetricStats]],
    sharding_run_metrics: dict[str, list[ShardingRunMetrics]],
    sharding_comparisons: dict[str, list[ShardingMetricComparison]],
) -> Path:
    output_path = output_dir / "summary_tables.csv"

    fieldnames = [
        "row_type",
        "group",
        "scenario",
        "role",
        "metric_name",
        "metric_label",
        "count",
        "median_seconds",
        "mean_seconds",
        "min_seconds",
        "max_seconds",
        "stdev_seconds",
        "baseline_median_seconds",
        "optimized_median_seconds",
        "difference_seconds",
        "relative_change_pct",
        "is_bottleneck",
        "run_id",
        "shard_count",
        "critical_path_seconds",
        "average_shard_seconds",
        "fastest_shard_seconds",
        "slowest_shard_seconds",
        "spread_seconds",
        "imbalance_ratio",
        "baseline_ratio",
        "optimized_ratio",
        "difference_ratio",
    ]
    scenario_lookup = {scenario.name: scenario for scenario in SCENARIOS}

    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for scenario in SCENARIOS:
            scenario_stats = stats_by_scenario.get(scenario.name, {})

            for metric_name, metric_stats in scenario_stats.items():
                writer.writerow(
                    {
                        "row_type": "scenario_stat",
                        "group": scenario.group,
                        "scenario": scenario.name,
                        "role": scenario.role,
                        "metric_name": metric_name,
                        "metric_label": humanize_metric_name(metric_name),
                        "count": metric_stats.count,
                        "median_seconds": seconds(metric_stats.median),
                        "mean_seconds": seconds(metric_stats.mean),
                        "min_seconds": seconds(metric_stats.minimum),
                        "max_seconds": seconds(metric_stats.maximum),
                        "stdev_seconds": seconds(metric_stats.stdev),
                        "baseline_median_seconds": "",
                        "optimized_median_seconds": "",
                        "difference_seconds": "",
                        "relative_change_pct": "",
                        "is_bottleneck": "",
                    }
                )

        for group_name, group_comparisons in comparisons.items():
            for comparison in group_comparisons:
                writer.writerow(
                    {
                        "row_type": "comparison",
                        "group": group_name,
                        "scenario": "",
                        "role": "",
                        "metric_name": comparison.metric_name,
                        "metric_label": humanize_metric_name(comparison.metric_name),
                        "count": "",
                        "median_seconds": "",
                        "mean_seconds": "",
                        "min_seconds": "",
                        "max_seconds": "",
                        "stdev_seconds": "",
                        "baseline_median_seconds": seconds(
                            comparison.baseline_median
                        ),
                        "optimized_median_seconds": seconds(
                            comparison.optimized_median
                        ),
                        "difference_seconds": seconds(comparison.difference),
                        "relative_change_pct": round(
                            comparison.relative_change_pct, 6
                        ),
                        "is_bottleneck": "",
                    }
                )

        for scenario_name, (metric_name, metric_stats) in bottlenecks.items():
            scenario = scenario_lookup.get(scenario_name)

            writer.writerow(
                {
                    "row_type": "bottleneck",
                    "group": scenario.group if scenario else "",
                    "scenario": scenario_name,
                    "role": scenario.role if scenario else "",
                    "metric_name": metric_name,
                    "metric_label": humanize_metric_name(metric_name),
                    "count": metric_stats.count,
                    "median_seconds": seconds(metric_stats.median),
                    "mean_seconds": seconds(metric_stats.mean),
                    "min_seconds": seconds(metric_stats.minimum),
                    "max_seconds": seconds(metric_stats.maximum),
                    "stdev_seconds": seconds(metric_stats.stdev),
                    "baseline_median_seconds": "",
                    "optimized_median_seconds": "",
                    "difference_seconds": "",
                    "relative_change_pct": "",
                    "is_bottleneck": "true",
                }
            )
        for scenario_name, run_metrics in sharding_run_metrics.items():
            scenario = scenario_lookup.get(scenario_name)

            for metric in run_metrics:
                writer.writerow(
                    {
                        "row_type": "sharding_run",
                        "group": scenario.group if scenario else "",
                        "scenario": scenario_name,
                        "role": scenario.role if scenario else "",
                        "metric_name": "sharding_run_metrics",
                        "metric_label": "Sharding run metrics",
                        "count": "",
                        "median_seconds": "",
                        "mean_seconds": "",
                        "min_seconds": "",
                        "max_seconds": "",
                        "stdev_seconds": "",
                        "baseline_median_seconds": "",
                        "optimized_median_seconds": "",
                        "difference_seconds": "",
                        "relative_change_pct": "",
                        "is_bottleneck": "",
                        "run_id": metric.run_id,
                        "shard_count": metric.shard_count,
                        "critical_path_seconds": seconds(
                            metric.critical_path_ms
                        ),
                        "average_shard_seconds": seconds(
                            metric.average_shard_ms
                        ),
                        "fastest_shard_seconds": seconds(
                            metric.fastest_shard_ms
                        ),
                        "slowest_shard_seconds": seconds(
                            metric.slowest_shard_ms
                        ),
                        "spread_seconds": seconds(metric.spread_ms),
                        "imbalance_ratio": round(metric.imbalance_ratio, 6),
                    }
                )

        for group_name, group_comparisons in sharding_comparisons.items():
            for comparison in group_comparisons:
                if comparison.metric_name == "imbalance_ratio":
                    baseline_seconds = ""
                    optimized_seconds = ""
                    difference_seconds = ""
                    imbalance_ratio = round(comparison.optimized_median, 6)
                    baseline_ratio = round(comparison.baseline_median, 6)
                    optimized_ratio = round(comparison.optimized_median, 6)
                    difference_ratio = round(comparison.difference, 6)
                else:
                    baseline_seconds = seconds(comparison.baseline_median)
                    optimized_seconds = seconds(comparison.optimized_median)
                    difference_seconds = seconds(comparison.difference)
                    imbalance_ratio = ""
                    baseline_ratio = ""
                    optimized_ratio = ""
                    difference_ratio = ""

                writer.writerow(
                    {
                        "row_type": "sharding_comparison",
                        "group": group_name,
                        "scenario": "",
                        "role": "",
                        "metric_name": comparison.metric_name,
                        "metric_label": humanize_metric_name(
                            comparison.metric_name
                        ),
                        "count": "",
                        "median_seconds": "",
                        "mean_seconds": "",
                        "min_seconds": "",
                        "max_seconds": "",
                        "stdev_seconds": "",
                        "baseline_median_seconds": baseline_seconds,
                        "optimized_median_seconds": optimized_seconds,
                        "difference_seconds": difference_seconds,
                        "relative_change_pct": round(
                            comparison.relative_change_pct, 6
                        ),
                        "is_bottleneck": "",
                        "run_id": "",
                        "shard_count": "",
                        "critical_path_seconds": "",
                        "average_shard_seconds": "",
                        "fastest_shard_seconds": "",
                        "slowest_shard_seconds": "",
                        "spread_seconds": "",
                        "imbalance_ratio": imbalance_ratio,
                        "baseline_ratio": baseline_ratio,
                        "optimized_ratio": optimized_ratio,
                        "difference_ratio": difference_ratio,
                    }
                )
    return output_path


def build_decision_notes(
    comparisons: dict[str, list[MetricComparison]],
    bottlenecks: dict[str, tuple[str, MetricStats]],
    sharding_comparisons: dict[str, list[ShardingMetricComparison]],
) -> list[str]:
    notes: list[str] = []

    def sharding_metric_map(
        group_name: str,
    ) -> dict[str, ShardingMetricComparison]:
        return {
            comparison.metric_name: comparison
            for comparison in sharding_comparisons.get(group_name, [])
        }

    dependency_comparisons = {
        comparison.metric_name: comparison
        for comparison in comparisons.get("dependency_cache", [])
    }
    dependency_total = dependency_comparisons.get("measured_total_duration_ms")
    dependency_prepare = dependency_comparisons.get(
        "dependency_prepare_duration_ms"
    )

    if dependency_prepare and dependency_total:
        notes.append(
            "Dependency cache reduced the dependency preparation phase "
            f"by {format_pct(dependency_prepare.relative_change_pct)} and the "
            f"measured total time by {format_pct(dependency_total.relative_change_pct)}."
        )

        dependency_bottleneck = bottlenecks.get("dependency_cache")
        if dependency_bottleneck:
            metric_name, metric_stats = dependency_bottleneck
            notes.append(
                "The main bottleneck in the optimized backend cache scenario is "
                f"{humanize_metric_name(metric_name)} "
                f"(median {format_ms(metric_stats.median)})."
            )

    docker_comparisons = {
        comparison.metric_name: comparison
        for comparison in comparisons.get("docker_build_cache", [])
    }
    docker_total = docker_comparisons.get("measured_total_duration_ms")
    docker_build = docker_comparisons.get("docker_build_duration_ms")

    if docker_build and docker_total:
        notes.append(
            "Docker build cache reduced the Docker build phase "
            f"by {format_pct(docker_build.relative_change_pct)} and the "
            f"measured total time by {format_pct(docker_total.relative_change_pct)}."
        )

        docker_bottleneck = bottlenecks.get("docker_baseline")
        if docker_bottleneck:
            metric_name, metric_stats = docker_bottleneck
            notes.append(
                "The main bottleneck in the Docker baseline scenario is "
                f"{humanize_metric_name(metric_name)} "
                f"(median {format_ms(metric_stats.median)})."
            )

    original_sharding = sharding_metric_map("sharding_original")
    original_critical_path = original_sharding.get("critical_path_ms")
    original_imbalance = original_sharding.get("imbalance_ratio")

    if original_critical_path:
        if original_critical_path.relative_change_pct < 0:
            notes.append(
                "On the original test suite, timing-based sharding reduced the "
                "critical path by "
                f"{format_pct(original_critical_path.relative_change_pct)}."
            )
        else:
            notes.append(
                "On the original test suite, timing-based sharding did not "
                "reduce the critical path. The median critical path changed by "
                f"{format_pct(original_critical_path.relative_change_pct)}, "
                "which indicates that the original workload had limited room "
                "for improvement."
            )

    if original_imbalance:
        notes.append(
            "On the original test suite, the imbalance ratio changed by "
            f"{format_pct(original_imbalance.relative_change_pct)}."
        )

    extended_sharding = sharding_metric_map("sharding_extended")
    extended_critical_path = extended_sharding.get("critical_path_ms")
    extended_imbalance = extended_sharding.get("imbalance_ratio")
    extended_spread = extended_sharding.get("spread_ms")

    if extended_critical_path:
        if extended_critical_path.relative_change_pct < 0:
            notes.append(
                "On the extended test suite, timing-based sharding reduced the "
                "critical path by "
                f"{format_pct(extended_critical_path.relative_change_pct)}, "
                "which indicates a measurable improvement of the parallel test "
                "execution path."
            )
        else:
            notes.append(
                "On the extended test suite, timing-based sharding did not "
                "reduce the critical path."
            )

    if extended_imbalance:
        notes.append(
            "On the extended test suite, the imbalance ratio changed by "
            f"{format_pct(extended_imbalance.relative_change_pct)}, "
            "which is used as an indicator of shard balance."
        )

    if extended_spread:
        notes.append(
            "On the extended test suite, the difference between the slowest "
            "and fastest shard changed by "
            f"{format_pct(extended_spread.relative_change_pct)}."
        )

    if original_critical_path and extended_critical_path:
        if (
            original_critical_path.relative_change_pct >= 0
            and extended_critical_path.relative_change_pct < 0
        ):
            notes.append(
                "The sharding results indicate that timing-based distribution "
                "is more useful when the test suite has sufficient granularity. "
                "This supports interpreting test-suite structure as a key "
                "condition for effective parallelization."
            )

    if not notes:
        notes.append(
            "No complete baseline/optimized comparison is available yet. "
            "Add metric files to the expected input scenario directories."
        )

    return notes


def write_summary_report_md(
    output_dir: Path,
    records_by_scenario: dict[str, list[dict[str, Any]]],
    stats_by_scenario: dict[str, dict[str, MetricStats]],
    comparisons: dict[str, list[MetricComparison]],
    bottlenecks: dict[str, tuple[str, MetricStats]],
    sharding_run_metrics: dict[str, list[ShardingRunMetrics]],
    sharding_comparisons: dict[str, list[ShardingMetricComparison]],
) -> Path:
    output_path = output_dir / "summary_report.md"

    lines: list[str] = []
    lines.append("# CI Experiment Analysis Report")
    lines.append("")
    lines.append(
        "This report was generated by `backend/scripts/analyze_ci_experiments.py`."
    )
    lines.append(
        "The tool processes metrics exported from GitHub Actions runs of the "
        "FastAPI thesis project."
    )
    lines.append("")

    lines.append("## 1. Scenario overview")
    lines.append("")
    lines.append("| Scenario | Group | Role | Records |")
    lines.append("|---|---|---:|---:|")

    for scenario in SCENARIOS:
        record_count = len(records_by_scenario.get(scenario.name, []))
        lines.append(
            f"| `{scenario.name}` | {scenario.group} | {scenario.role} | "
            f"{record_count} |"
        )

    lines.append("")
    lines.append("## 2. Metric statistics")
    lines.append("")

    any_stats = False

    for scenario in SCENARIOS:
        scenario_stats = stats_by_scenario.get(scenario.name, {})
        if not scenario_stats:
            continue

        any_stats = True
        lines.append(f"### {scenario.name}")
        lines.append("")
        lines.append(
            "| Metric | Count | Median [s] | Mean [s] | Min [s] | Max [s] | Stdev [s] |"
        )
        lines.append("|---|---:|---:|---:|---:|---:|---:|")

        for metric_name, metric_stats in scenario_stats.items():
            lines.append(
                f"| {humanize_metric_name(metric_name)} "
                f"| {metric_stats.count} "
                f"| {seconds(metric_stats.median):.3f} "
                f"| {seconds(metric_stats.mean):.3f} "
                f"| {seconds(metric_stats.minimum):.3f} "
                f"| {seconds(metric_stats.maximum):.3f} "
                f"| {seconds(metric_stats.stdev):.3f} |"
            )

        lines.append("")

    if not any_stats:
        lines.append("No numeric metrics are available yet.")
        lines.append("")

    lines.append("## 3. Baseline vs optimized comparisons")
    lines.append("")

    if comparisons:
        for group_name, group_comparisons in comparisons.items():
            if not group_comparisons:
                continue

            lines.append(f"### {group_name}")
            lines.append("")
            lines.append(
                "| Metric | Baseline median [s] | Optimized median [s] | "
                "Difference [s] | Relative change |"
            )
            lines.append("|---|---:|---:|---:|---:|")

            for comparison in group_comparisons:
                lines.append(
                    f"| {humanize_metric_name(comparison.metric_name)} "
                    f"| {seconds(comparison.baseline_median):.3f} "
                    f"| {seconds(comparison.optimized_median):.3f} "
                    f"| {seconds(comparison.difference):.3f} "
                    f"| {format_pct(comparison.relative_change_pct)} |"
                )

            lines.append("")
    else:
        lines.append("No complete comparison pairs are available yet.")
        lines.append("")

    lines.append("## 4. Detected bottlenecks")
    lines.append("")

    if bottlenecks:
        lines.append("| Scenario | Bottleneck metric | Median [s] |")
        lines.append("|---|---|---:|")

        for scenario in SCENARIOS:
            bottleneck = bottlenecks.get(scenario.name)
            if bottleneck is None:
                continue

            metric_name, metric_stats = bottleneck
            lines.append(
                f"| `{scenario.name}` | {humanize_metric_name(metric_name)} "
                f"| {seconds(metric_stats.median):.3f} |"
            )

        lines.append("")
    else:
        lines.append("No bottlenecks are available yet.")
        lines.append("")

    lines.append("## 5. Sharding run-level metrics")
    lines.append("")

    if sharding_run_metrics:
        for scenario_name in SHARDING_SCENARIO_NAMES:
            run_metrics = sharding_run_metrics.get(scenario_name)
            if not run_metrics:
                continue

            lines.append(f"### {scenario_name}")
            lines.append("")
            lines.append(
                "| Run | Shards | Critical path [s] | Average shard [s] | "
                "Spread [s] | Imbalance ratio |"
            )
            lines.append("|---|---:|---:|---:|---:|---:|")

            for metric in run_metrics:
                lines.append(
                    f"| {metric.run_id} "
                    f"| {metric.shard_count} "
                    f"| {seconds(metric.critical_path_ms):.3f} "
                    f"| {seconds(metric.average_shard_ms):.3f} "
                    f"| {seconds(metric.spread_ms):.3f} "
                    f"| {format_ratio(metric.imbalance_ratio)} |"
                )

            lines.append("")
            lines.append("Summary:")
            lines.append("")
            lines.append(
                "| Metric | Count | Median | Mean | Min | Max | Stdev |"
            )
            lines.append("|---|---:|---:|---:|---:|---:|---:|")

            summary = summarize_sharding_run_metrics(run_metrics)
            for metric_name, metric_stats in summary.items():
                lines.append(
                    f"| {humanize_metric_name(metric_name)} "
                    f"| {metric_stats.count} "
                    f"| {format_metric_summary_value(metric_name, metric_stats.median)} "
                    f"| {format_metric_summary_value(metric_name, metric_stats.mean)} "
                    f"| {format_metric_summary_value(metric_name, metric_stats.minimum)} "
                    f"| {format_metric_summary_value(metric_name, metric_stats.maximum)} "
                    f"| {format_metric_summary_value(metric_name, metric_stats.stdev)} |"
                )

            lines.append("")
    else:
        lines.append("No sharding run-level metrics are available yet.")
        lines.append("")



    lines.append("## 6. Sharding baseline vs timing-based comparisons")
    lines.append("")

    if sharding_comparisons:
        for group_name, group_comparisons in sharding_comparisons.items():
            lines.append(f"### {group_name}")
            lines.append("")
            lines.append(
                "| Metric | Baseline median | Timing-based median | "
                "Difference | Relative change |"
            )
            lines.append("|---|---:|---:|---:|---:|")

            for comparison in group_comparisons:
                if comparison.metric_name == "imbalance_ratio":
                    baseline_value = format_ratio(comparison.baseline_median)
                    optimized_value = format_ratio(
                        comparison.optimized_median
                    )
                    difference_value = format_ratio(comparison.difference)
                else:
                    baseline_value = f"{seconds(comparison.baseline_median):.3f} s"
                    optimized_value = (
                        f"{seconds(comparison.optimized_median):.3f} s"
                    )
                    difference_value = f"{seconds(comparison.difference):.3f} s"

                lines.append(
                    f"| {humanize_metric_name(comparison.metric_name)} "
                    f"| {baseline_value} "
                    f"| {optimized_value} "
                    f"| {difference_value} "
                    f"| {format_pct(comparison.relative_change_pct)} |"
                )

            lines.append("")
    else:
        lines.append("No sharding comparison pairs are available yet.")
        lines.append("")

    lines.append("## 7. Decision notes")
    lines.append("")

    for note in build_decision_notes(
        comparisons,
        bottlenecks,
        sharding_comparisons,
    ):
        lines.append(f"- {note}")

    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def print_sharding_run_summary(
    sharding_run_metrics: dict[str, list[ShardingRunMetrics]],
) -> None:
    print()
    print("Sharding run-level metrics:")

    if not sharding_run_metrics:
        print("- No sharding run metrics available yet.")
        return

    for scenario_name in SHARDING_SCENARIO_NAMES:
        run_metrics = sharding_run_metrics.get(scenario_name)
        if not run_metrics:
            continue

        print(f"\n{scenario_name}:")

        for metric in run_metrics:
            print(
                f"- {metric.run_id}: "
                f"critical_path={format_ms(metric.critical_path_ms)}, "
                f"average_shard={format_ms(metric.average_shard_ms)}, "
                f"spread={format_ms(metric.spread_ms)}, "
                f"imbalance_ratio={format_ratio(metric.imbalance_ratio)}"
            )

        summary = summarize_sharding_run_metrics(run_metrics)

        print("  Summary:")
        for metric_name, stats in summary.items():
            if metric_name == "imbalance_ratio":
                print(
                    f"  - {humanize_metric_name(metric_name)}: "
                    f"count={stats.count}, "
                    f"median={format_ratio(stats.median)}, "
                    f"mean={format_ratio(stats.mean)}, "
                    f"min={format_ratio(stats.minimum)}, "
                    f"max={format_ratio(stats.maximum)}, "
                    f"stdev={format_ratio(stats.stdev)}"
                )
            else:
                print(
                    f"  - {humanize_metric_name(metric_name)}: "
                    f"count={stats.count}, "
                    f"median={format_ms(stats.median)}, "
                    f"mean={format_ms(stats.mean)}, "
                    f"min={format_ms(stats.minimum)}, "
                    f"max={format_ms(stats.maximum)}, "
                    f"stdev={format_ms(stats.stdev)}"
                )



def print_sharding_comparison_summary(
    sharding_comparisons: dict[str, list[ShardingMetricComparison]],
) -> None:
    print()
    print("Sharding baseline vs timing-based comparisons:")

    if not sharding_comparisons:
        print("- No sharding comparison pairs available yet.")
        return

    for group_name, comparisons in sharding_comparisons.items():
        print(f"\n{group_name}:")

        for comparison in comparisons:
            if comparison.metric_name == "imbalance_ratio":
                baseline_value = format_ratio(comparison.baseline_median)
                optimized_value = format_ratio(comparison.optimized_median)
                difference_value = format_ratio(comparison.difference)
            else:
                baseline_value = format_ms(comparison.baseline_median)
                optimized_value = format_ms(comparison.optimized_median)
                difference_value = format_ms(comparison.difference)

            print(
                f"- {humanize_metric_name(comparison.metric_name)}: "
                f"baseline={baseline_value}, "
                f"optimized={optimized_value}, "
                f"difference={difference_value}, "
                f"relative_change={format_pct(comparison.relative_change_pct)}"
            )


def print_bottleneck_summary(
    bottlenecks: dict[str, tuple[str, MetricStats]],
) -> None:
    print()
    print("Detected bottlenecks:")

    if not bottlenecks:
        print("- No bottlenecks detected yet.")
        return

    for scenario in SCENARIOS:
        bottleneck = bottlenecks.get(scenario.name)
        if bottleneck is None:
            continue

        metric_name, metric_stats = bottleneck
        print(
            f"- {scenario.name}: "
            f"{humanize_metric_name(metric_name)} "
            f"(median={format_ms(metric_stats.median)})"
        )


def main() -> None:
    args = parse_args()

    input_dir: Path = args.input
    output_dir: Path = args.output

    output_dir.mkdir(parents=True, exist_ok=True)

    print("CI experiment analyzer")
    print(f"Input directory:  {input_dir}")
    print(f"Output directory: {output_dir}")
    print()

    errors = validate_input_structure(
        input_dir,
        allow_missing_scenarios=args.allow_missing_scenarios,
    )
    loaded_records = print_scenario_overview(input_dir)

    if errors:
        print()
        print("Input validation failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    total_records = sum(len(records) for records in loaded_records.values())
    stats_by_scenario = compute_scenario_stats(loaded_records)
    comparisons = compute_comparisons(stats_by_scenario)
    sharding_run_metrics = compute_sharding_run_metrics(loaded_records)
    sharding_comparisons = compute_sharding_comparisons(sharding_run_metrics)
    bottlenecks = detect_bottlenecks(stats_by_scenario)

    computed_metrics_payload = build_computed_metrics_payload(
        records_by_scenario=loaded_records,
        stats_by_scenario=stats_by_scenario,
        comparisons=comparisons,
        bottlenecks=bottlenecks,
        sharding_run_metrics=sharding_run_metrics,
        sharding_comparisons=sharding_comparisons,
    )
    
    computed_metrics_path = write_computed_metrics_json(
        output_dir=output_dir,
        payload=computed_metrics_payload,
    )

    summary_tables_path = write_summary_tables_csv(
        output_dir=output_dir,
        stats_by_scenario=stats_by_scenario,
        comparisons=comparisons,
        bottlenecks=bottlenecks,
        sharding_run_metrics=sharding_run_metrics,
        sharding_comparisons=sharding_comparisons,
    )

    summary_report_path = write_summary_report_md(
        output_dir=output_dir,
        records_by_scenario=loaded_records,
        stats_by_scenario=stats_by_scenario,
        comparisons=comparisons,
        bottlenecks=bottlenecks,
        sharding_run_metrics=sharding_run_metrics,
        sharding_comparisons=sharding_comparisons,
    )

    print()
    print(f"Total loaded metric records: {total_records}")
    print_stats_summary(stats_by_scenario)
    print_comparison_summary(comparisons)
    print_sharding_run_summary(sharding_run_metrics)
    print_sharding_comparison_summary(sharding_comparisons)
    print_bottleneck_summary(bottlenecks)
    print()
    print(f"Wrote computed metrics: {computed_metrics_path}")
    print(f"Wrote summary tables:   {summary_tables_path}")
    print(f"Wrote summary report:   {summary_report_path}")
    print(
        "Status: metric statistics, comparisons, sharding run metrics, "
        "sharding comparisons, bottlenecks, JSON output, CSV tables, "
        "and Markdown report are available"
    )

if __name__ == "__main__":
    main()