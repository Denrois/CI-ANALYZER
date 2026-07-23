"""Domain models for CI experiment configuration."""

from collections.abc import Mapping
from dataclasses import dataclass, field
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
class AnalysisConfig:
    """Configurable thresholds for higher-level analysis."""

    local_improvement_threshold_pct: float = 10.0
    total_impact_threshold_pct: float = 5.0


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    """Complete experiment configuration."""

    version: int
    experiment: ExperimentMetadata
    scenarios: tuple[ScenarioConfig, ...]
    record_mapping: Mapping[str, str]
    metrics: tuple[MetricConfig, ...]
    comparisons: tuple[ComparisonConfig, ...]
    analysis: AnalysisConfig = field(
        default_factory=AnalysisConfig
    )


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
class MetricStats:
    """Descriptive statistics for one scenario metric."""

    metric_id: str
    unit: str
    role: str
    count: int
    median: float
    mean: float
    minimum: float
    maximum: float
    standard_deviation: float


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    """Descriptive statistics calculated for one scenario."""

    scenario_id: str
    metrics: tuple[MetricStats, ...]


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


@dataclass(frozen=True, slots=True)
class LocalTotalImpactResult:
    """Relationship between one local phase and total scenario impact."""

    comparison_id: str
    phase_metric_id: str
    total_metric_id: str
    phase_relative_difference_percent: float | None
    total_relative_difference_percent: float | None


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Complete result of one configured experiment analysis."""

    version: int
    experiment: ExperimentMetadata
    scenarios: tuple[ScenarioResult, ...]
    comparisons: tuple[ComparisonResult, ...]
    local_total_impacts: tuple[LocalTotalImpactResult, ...] = ()