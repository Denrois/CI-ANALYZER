"""Tests for analysis report serialization."""

from ci_experiment_analyzer.models import (
    AnalysisResult,
    ComparisonResult,
    ExperimentMetadata,
    LocalTotalImpactResult,
    MetricComparisonResult,
    MetricStats,
    ScenarioResult,
)
from ci_experiment_analyzer.reports import analysis_result_to_dict


def test_analysis_result_has_stable_json_structure() -> None:
    """A complete analysis should have deterministic report structure."""
    result = AnalysisResult(
        version=1,
        experiment=ExperimentMetadata(
            id="cache-example",
            title="Cache example",
        ),
        scenarios=(
            ScenarioResult(
                scenario_id="baseline",
                metrics=(
                    MetricStats(
                        metric_id="total_duration",
                        unit="milliseconds",
                        role="total",
                        count=2,
                        median=55_000.0,
                        mean=55_000.0,
                        minimum=50_000.0,
                        maximum=60_000.0,
                        standard_deviation=7_071.067811865475,
                    ),
                ),
            ),
            ScenarioResult(
                scenario_id="optimized",
                metrics=(
                    MetricStats(
                        metric_id="total_duration",
                        unit="milliseconds",
                        role="total",
                        count=2,
                        median=48_000.0,
                        mean=48_000.0,
                        minimum=45_000.0,
                        maximum=51_000.0,
                        standard_deviation=4_242.640687119285,
                    ),
                ),
            ),
        ),
        comparisons=(
            ComparisonResult(
                comparison_id="cache-impact",
                baseline_scenario_id="baseline",
                candidate_scenario_id="optimized",
                metrics=(
                    MetricComparisonResult(
                        metric_id="total_duration",
                        unit="milliseconds",
                        baseline_median=55_000.0,
                        candidate_median=48_000.0,
                        absolute_difference=-7_000.0,
                        relative_difference_percent=(
                            -12.727272727272727
                        ),
                    ),
                ),
            ),
        ),
        local_total_impacts=(
            LocalTotalImpactResult(
                comparison_id="cache-impact",
                phase_metric_id="install_duration",
                total_metric_id="total_duration",
                phase_relative_difference_percent=-25.0,
                total_relative_difference_percent=(
                    -12.727272727272727
                ),
            ),
        ),
    )

    assert analysis_result_to_dict(result) == {
        "version": 1,
        "experiment": {
            "id": "cache-example",
            "title": "Cache example",
        },
        "scenarios": [
            {
                "id": "baseline",
                "metrics": [
                    {
                        "id": "total_duration",
                        "unit": "milliseconds",
                        "role": "total",
                        "count": 2,
                        "median": 55_000.0,
                        "mean": 55_000.0,
                        "minimum": 50_000.0,
                        "maximum": 60_000.0,
                        "standard_deviation": (
                            7_071.067811865475
                        ),
                    }
                ],
            },
            {
                "id": "optimized",
                "metrics": [
                    {
                        "id": "total_duration",
                        "unit": "milliseconds",
                        "role": "total",
                        "count": 2,
                        "median": 48_000.0,
                        "mean": 48_000.0,
                        "minimum": 45_000.0,
                        "maximum": 51_000.0,
                        "standard_deviation": (
                            4_242.640687119285
                        ),
                    }
                ],
            },
        ],
        "comparisons": [
            {
                "id": "cache-impact",
                "baseline": "baseline",
                "candidate": "optimized",
                "metrics": [
                    {
                        "id": "total_duration",
                        "unit": "milliseconds",
                        "baseline_median": 55_000.0,
                        "candidate_median": 48_000.0,
                        "absolute_difference": -7_000.0,
                        "relative_difference_percent": (
                            -12.727272727272727
                        ),
                    }
                ],
            }
        ],
        "local_vs_total_impacts": [
            {
                "comparison": "cache-impact",
                "phase_metric": "install_duration",
                "total_metric": "total_duration",
                "phase_relative_difference_percent": -25.0,
                "total_relative_difference_percent": (
                    -12.727272727272727
                ),
            }
        ],
    }