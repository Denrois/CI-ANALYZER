"""Tests for analysis report serialization."""

from ci_experiment_analyzer.models import (
    AnalysisResult,
    BottleneckCandidateResult,
    ComparisonResult,
    ExperimentMetadata,
    LocalTotalImpactResult,
    MetricComparisonResult,
    MetricStats,
    ParallelAnalysisResult,
    ParallelMetricStats,
    ParallelRunMetrics,
    ParallelScenarioResult,
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
                local_improvement_threshold_pct=10.0,
                total_impact_threshold_pct=5.0,
                substantial_local_improvement=True,
                limited_total_improvement=False,
                limited_end_to_end_impact=False,
                warning=None,
            ),
        ),
        bottleneck_candidates=(
            BottleneckCandidateResult(
                scenario_id="baseline",
                phase_metric_ids=(
                    "install_duration",
                ),
                median=12_000.0,
                unit="milliseconds",
                is_tie=False,
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
                "local_improvement_threshold_pct": 10.0,
                "total_impact_threshold_pct": 5.0,
                "substantial_local_improvement": True,
                "limited_total_improvement": False,
                "limited_end_to_end_impact": False,
                "warning": None,
            }
        ],
        "bottleneck_candidates": [
            {
                "scenario": "baseline",
                "phase_metrics": [
                    "install_duration",
                ],
                "median": 12_000.0,
                "unit": "milliseconds",
                "is_tie": False,
            }
        ],
        "parallel_analyses": [],
    }


def _parallel_stats(
    value: float,
) -> ParallelMetricStats:
    """Create deterministic parallel statistics."""
    return ParallelMetricStats(
        count=1,
        median=value,
        mean=value,
        minimum=value,
        maximum=value,
        standard_deviation=0.0,
    )


def test_analysis_result_to_dict_serializes_parallel_analysis() -> None:
    """Parallel analysis should preserve run and aggregate details."""
    baseline = ParallelScenarioResult(
        scenario_id="baseline",
        duration_unit="milliseconds",
        runs=(
            ParallelRunMetrics(
                run_id="run-1",
                branch_count=2,
                critical_path_duration=40_000.0,
                minimum_branch_duration=20_000.0,
                mean_branch_duration=30_000.0,
                spread=20_000.0,
                imbalance_ratio=4.0 / 3.0,
                slowest_branch_ids=("shard-1",),
                is_slowest_tie=False,
            ),
        ),
        branch_count_minimum=2,
        branch_count_maximum=2,
        branch_count_consistent=True,
        critical_path_duration=_parallel_stats(
            40_000.0
        ),
        spread=_parallel_stats(20_000.0),
        imbalance_ratio=_parallel_stats(
            4.0 / 3.0
        ),
    )

    candidate = ParallelScenarioResult(
        scenario_id="timing-based",
        duration_unit="milliseconds",
        runs=(
            ParallelRunMetrics(
                run_id="run-1",
                branch_count=2,
                critical_path_duration=30_000.0,
                minimum_branch_duration=30_000.0,
                mean_branch_duration=30_000.0,
                spread=0.0,
                imbalance_ratio=1.0,
                slowest_branch_ids=(
                    "shard-1",
                    "shard-2",
                ),
                is_slowest_tie=True,
            ),
        ),
        branch_count_minimum=2,
        branch_count_maximum=2,
        branch_count_consistent=True,
        critical_path_duration=_parallel_stats(
            30_000.0
        ),
        spread=_parallel_stats(0.0),
        imbalance_ratio=_parallel_stats(1.0),
    )

    result = AnalysisResult(
        version=1,
        experiment=ExperimentMetadata(
            id="parallel-example",
            title="Parallel example",
        ),
        scenarios=(),
        comparisons=(),
        parallel_analyses=(
            ParallelAnalysisResult(
                analysis_id="test-sharding",
                duration_metric_id=(
                    "branch_duration"
                ),
                baseline=baseline,
                candidate=candidate,
                metrics=(
                    MetricComparisonResult(
                        metric_id=(
                            "critical_path_duration"
                        ),
                        unit="milliseconds",
                        baseline_median=40_000.0,
                        candidate_median=30_000.0,
                        absolute_difference=-10_000.0,
                        relative_difference_percent=-25.0,
                    ),
                ),
            ),
        ),
    )

    report = analysis_result_to_dict(result)

    assert len(report["parallel_analyses"]) == 1

    parallel_analysis = report[
        "parallel_analyses"
    ][0]

    assert parallel_analysis["id"] == "test-sharding"
    assert (
        parallel_analysis["duration_metric"]
        == "branch_duration"
    )

    baseline_report = parallel_analysis["baseline"]

    assert baseline_report["scenario"] == "baseline"
    assert baseline_report["duration_unit"] == (
        "milliseconds"
    )
    assert baseline_report["branch_count"] == {
        "minimum": 2,
        "maximum": 2,
        "consistent": True,
    }

    baseline_run = baseline_report["runs"][0]

    assert baseline_run["run_id"] == "run-1"
    assert baseline_run["branch_count"] == 2
    assert (
        baseline_run["critical_path_duration"]
        == 40_000.0
    )
    assert baseline_run["slowest_branches"] == [
        "shard-1",
    ]
    assert baseline_run["is_slowest_tie"] is False

    assert parallel_analysis["metrics"] == [
        {
            "id": "critical_path_duration",
            "unit": "milliseconds",
            "baseline_median": 40_000.0,
            "candidate_median": 30_000.0,
            "absolute_difference": -10_000.0,
            "relative_difference_percent": -25.0,
        }
    ]