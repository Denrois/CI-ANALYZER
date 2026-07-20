"""Domain models for CI experiment configuration."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ExperimentMetadata:
    """Basic experiment information."""

    id: str
    title: str


@dataclass(frozen=True, slots=True)
class SourceConfig:
    """Input source associated with a scenario."""

    format: str
    path: Path


@dataclass(frozen=True, slots=True)
class ScenarioConfig:
    """A measured experiment scenario."""

    id: str
    source: SourceConfig


@dataclass(frozen=True, slots=True)
class MetricConfig:
    """A numeric metric loaded from scenario records."""

    id: str
    field: str
    metric_type: str
    unit: str
    role: str


@dataclass(frozen=True, slots=True)
class ComparisonConfig:
    """A comparison between baseline and candidate scenarios."""

    id: str
    baseline: str
    candidate: str
    metrics: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    """Complete experiment configuration."""

    version: int
    experiment: ExperimentMetadata
    scenarios: tuple[ScenarioConfig, ...]
    record_mapping: Mapping[str, str]
    metrics: tuple[MetricConfig, ...]
    comparisons: tuple[ComparisonConfig, ...]


@dataclass(frozen=True, slots=True)
class RunRecord:
    """One measured CI experiment run."""

    run_id: str
    metric_values: Mapping[str, float]


@dataclass(frozen=True, slots=True)
class ScenarioDataset:
    """All measured runs belonging to one scenario."""

    scenario_id: str
    records: tuple[RunRecord, ...]


@dataclass(frozen=True, slots=True)
class MetricComparisonResult:
    """Comparison result for one metric."""

    metric_id: str
    unit: str
    baseline_median: float
    candidate_median: float
    absolute_difference: float
    relative_difference_percent: float | None


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    """Result of comparing two experiment scenarios."""

    comparison_id: str
    baseline_scenario_id: str
    candidate_scenario_id: str
    metrics: tuple[MetricComparisonResult, ...]