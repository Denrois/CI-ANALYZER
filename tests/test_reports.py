"""Tests for analysis report serialization."""

import csv
import json
from io import StringIO
from pathlib import Path

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
from ci_experiment_analyzer.reports import (
    analysis_result_to_dict,
    analysis_result_to_markdown,
    comparison_summary_to_csv,
    write_analysis_reports,
)


def test_markdown_report_has_stable_empty_structure() -> None:
    """An empty result should still produce a complete report."""
    result = AnalysisResult(
        version=1,
        experiment=ExperimentMetadata(
            id="empty-example",
            title="Empty example",
        ),
        scenarios=(),
        comparisons=(),
    )

    assert analysis_result_to_markdown(result) == (
        "# Empty example\n"
        "\n"
        "Experiment ID: `empty-example`\n"
        "\n"
        "## Overview\n"
        "\n"
        "- Configuration version: `1`\n"
        "- Scenario results: `0`\n"
        "- Ordinary comparisons: `0`\n"
        "- Parallel analyses: `0`\n"
        "\n"
        "## Scenario statistics\n"
        "\n"
        "No scenario statistics were produced.\n"
        "\n"
        "## Comparisons\n"
        "\n"
        "No ordinary comparisons were configured.\n"
        "\n"
        "## Local-versus-total impact\n"
        "\n"
        "No local-versus-total impact "
        "classifications were produced.\n"
        "\n"
        "## Bottleneck candidates\n"
        "\n"
        "No bottleneck candidates were identified.\n"
        "\n"
        "## Parallel-stage analysis\n"
        "\n"
        "No parallel analyses were configured.\n"
        "\n"
        "## Warnings\n"
        "\n"
        "No warnings.\n"
        "\n"
        "## Limitations\n"
        "\n"
        "- Comparisons use scenario medians.\n"
        "- Bottleneck candidates are based only on "
        "configured measured phase durations.\n"
        "- Parallel critical-path duration covers only "
        "the configured parallel stage.\n"
        "- The report does not reconstruct the dependency "
        "graph of the complete CI pipeline.\n"
    )


def test_comparison_summary_csv_has_stable_empty_structure() -> None:
    """A result without comparisons should still contain a header."""
    result = AnalysisResult(
        version=1,
        experiment=ExperimentMetadata(
            id="empty-example",
            title="Empty example",
        ),
        scenarios=(),
        comparisons=(),
    )

    assert comparison_summary_to_csv(result) == (
        "analysis_type,analysis_id,baseline_scenario,"
        "candidate_scenario,source_metric_id,metric_id,"
        "unit,baseline_median,candidate_median,"
        "absolute_difference,relative_difference_percent\n"
    )


def test_write_analysis_reports_writes_all_formats(
    tmp_path: Path,
) -> None:
    """All supported report formats should be written together."""
    result = AnalysisResult(
        version=1,
        experiment=ExperimentMetadata(
            id="file-output-example",
            title="File output example",
        ),
        scenarios=(),
        comparisons=(),
    )

    output_directory = tmp_path / "nested" / "report"

    report_paths = write_analysis_reports(
        result,
        output_directory,
    )

    assert report_paths.analysis_json == (output_directory / "analysis.json")
    assert report_paths.summary_csv == (output_directory / "summary.csv")
    assert report_paths.report_markdown == (output_directory / "report.md")

    assert report_paths.analysis_json.is_file()
    assert report_paths.summary_csv.is_file()
    assert report_paths.report_markdown.is_file()

    json_content = json.loads(report_paths.analysis_json.read_text(encoding="utf-8"))

    assert json_content == analysis_result_to_dict(result)

    assert report_paths.summary_csv.read_text(encoding="utf-8") == comparison_summary_to_csv(result)

    assert report_paths.report_markdown.read_text(encoding="utf-8") == analysis_result_to_markdown(
        result
    )


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
                        relative_difference_percent=(-12.727272727272727),
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
                total_relative_difference_percent=(-12.727272727272727),
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
                phase_metric_ids=("install_duration",),
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
                        "standard_deviation": (7_071.067811865475),
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
                        "standard_deviation": (4_242.640687119285),
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
                        "relative_difference_percent": (-12.727272727272727),
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
                "total_relative_difference_percent": (-12.727272727272727),
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


def test_markdown_report_includes_all_analysis_sections() -> None:
    """Markdown should include ordinary and parallel analysis details."""
    baseline = ParallelScenarioResult(
        scenario_id="baseline",
        duration_unit="milliseconds",
        runs=(
            ParallelRunMetrics(
                run_id="baseline-1",
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
        branch_count_maximum=3,
        branch_count_consistent=False,
        critical_path_duration=_parallel_stats(40_000.0),
        spread=_parallel_stats(20_000.0),
        imbalance_ratio=_parallel_stats(4.0 / 3.0),
    )

    candidate = ParallelScenarioResult(
        scenario_id="timing-based",
        duration_unit="milliseconds",
        runs=(
            ParallelRunMetrics(
                run_id="candidate-1",
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
        critical_path_duration=_parallel_stats(30_000.0),
        spread=_parallel_stats(0.0),
        imbalance_ratio=_parallel_stats(1.0),
    )

    result = AnalysisResult(
        version=1,
        experiment=ExperimentMetadata(
            id="markdown-example",
            title="Markdown example",
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
                        relative_difference_percent=(-12.727272727272727),
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
                total_relative_difference_percent=-2.0,
                local_improvement_threshold_pct=10.0,
                total_impact_threshold_pct=5.0,
                substantial_local_improvement=True,
                limited_total_improvement=True,
                limited_end_to_end_impact=True,
                warning=(
                    "The local phase improved substantially, but total impact remained limited."
                ),
            ),
        ),
        bottleneck_candidates=(
            BottleneckCandidateResult(
                scenario_id="baseline",
                phase_metric_ids=(
                    "build_duration",
                    "test_duration",
                ),
                median=20_000.0,
                unit="milliseconds",
                is_tie=True,
            ),
        ),
        parallel_analyses=(
            ParallelAnalysisResult(
                analysis_id="test-sharding",
                duration_metric_id="shard_duration",
                baseline=baseline,
                candidate=candidate,
                metrics=(
                    MetricComparisonResult(
                        metric_id=("critical_path_duration"),
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

    content = analysis_result_to_markdown(result)

    assert content.startswith("# Markdown example\n")

    assert "## Scenario statistics" in content
    assert "total_duration" in content
    assert "55000" in content

    assert "## Comparisons" in content
    assert "`cache-impact`" in content
    assert "-12.727273%" in content

    assert "## Local-versus-total impact" in content
    assert "install_duration" in content

    assert "## Bottleneck candidates" in content
    assert "build_duration, test_duration" in content

    assert "## Parallel-stage analysis" in content
    assert "`test-sharding`" in content
    assert "baseline-1" in content
    assert "candidate-1" in content
    assert "shard-1, shard-2" in content

    assert "## Warnings" in content
    assert "The local phase improved substantially, but total impact remained limited." in content
    assert "branch count varies from 2 to 3" in content

    assert content.index("## Scenario statistics") < content.index("## Comparisons")
    assert content.index("## Comparisons") < content.index("## Parallel-stage analysis")


def test_comparison_summary_csv_flattens_all_comparisons() -> None:
    """Ordinary and parallel comparisons should share one CSV schema."""
    baseline = ParallelScenarioResult(
        scenario_id="baseline",
        duration_unit="milliseconds",
        runs=(),
        branch_count_minimum=2,
        branch_count_maximum=2,
        branch_count_consistent=True,
        critical_path_duration=_parallel_stats(40_000.0),
        spread=_parallel_stats(20_000.0),
        imbalance_ratio=_parallel_stats(4.0 / 3.0),
    )

    candidate = ParallelScenarioResult(
        scenario_id="timing-based",
        duration_unit="milliseconds",
        runs=(),
        branch_count_minimum=2,
        branch_count_maximum=2,
        branch_count_consistent=True,
        critical_path_duration=_parallel_stats(30_000.0),
        spread=_parallel_stats(0.0),
        imbalance_ratio=_parallel_stats(1.0),
    )

    result = AnalysisResult(
        version=1,
        experiment=ExperimentMetadata(
            id="summary-example",
            title="Summary example",
        ),
        scenarios=(),
        comparisons=(
            ComparisonResult(
                comparison_id="cache-impact",
                baseline_scenario_id="baseline",
                candidate_scenario_id="optimized",
                metrics=(
                    MetricComparisonResult(
                        metric_id="total_duration",
                        unit="milliseconds",
                        baseline_median=0.0,
                        candidate_median=1_000.0,
                        absolute_difference=1_000.0,
                        relative_difference_percent=None,
                    ),
                ),
            ),
        ),
        parallel_analyses=(
            ParallelAnalysisResult(
                analysis_id="test-sharding",
                duration_metric_id="shard_duration",
                baseline=baseline,
                candidate=candidate,
                metrics=(
                    MetricComparisonResult(
                        metric_id=("critical_path_duration"),
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

    content = comparison_summary_to_csv(result)

    assert content.splitlines()[0] == (
        "analysis_type,analysis_id,baseline_scenario,"
        "candidate_scenario,source_metric_id,metric_id,"
        "unit,baseline_median,candidate_median,"
        "absolute_difference,relative_difference_percent"
    )

    rows = list(csv.DictReader(StringIO(content)))

    assert rows == [
        {
            "analysis_type": "comparison",
            "analysis_id": "cache-impact",
            "baseline_scenario": "baseline",
            "candidate_scenario": "optimized",
            "source_metric_id": "total_duration",
            "metric_id": "total_duration",
            "unit": "milliseconds",
            "baseline_median": "0.0",
            "candidate_median": "1000.0",
            "absolute_difference": "1000.0",
            "relative_difference_percent": "",
        },
        {
            "analysis_type": "parallel_analysis",
            "analysis_id": "test-sharding",
            "baseline_scenario": "baseline",
            "candidate_scenario": "timing-based",
            "source_metric_id": "shard_duration",
            "metric_id": "critical_path_duration",
            "unit": "milliseconds",
            "baseline_median": "40000.0",
            "candidate_median": "30000.0",
            "absolute_difference": "-10000.0",
            "relative_difference_percent": "-25.0",
        },
    ]


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
        critical_path_duration=_parallel_stats(40_000.0),
        spread=_parallel_stats(20_000.0),
        imbalance_ratio=_parallel_stats(4.0 / 3.0),
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
        critical_path_duration=_parallel_stats(30_000.0),
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
                duration_metric_id=("branch_duration"),
                baseline=baseline,
                candidate=candidate,
                metrics=(
                    MetricComparisonResult(
                        metric_id=("critical_path_duration"),
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

    parallel_analysis = report["parallel_analyses"][0]

    assert parallel_analysis["id"] == "test-sharding"
    assert parallel_analysis["duration_metric"] == "branch_duration"

    baseline_report = parallel_analysis["baseline"]

    assert baseline_report["scenario"] == "baseline"
    assert baseline_report["duration_unit"] == ("milliseconds")
    assert baseline_report["branch_count"] == {
        "minimum": 2,
        "maximum": 2,
        "consistent": True,
    }

    baseline_run = baseline_report["runs"][0]

    assert baseline_run["run_id"] == "run-1"
    assert baseline_run["branch_count"] == 2
    assert baseline_run["critical_path_duration"] == 40_000.0
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
