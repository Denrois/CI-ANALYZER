"""Coordinate configured CI experiment analysis."""

from ci_experiment_analyzer.bottlenecks import (
    identify_bottleneck_candidate,
)
from ci_experiment_analyzer.comparisons import compare_scenarios
from ci_experiment_analyzer.impact import calculate_local_total_impacts
from ci_experiment_analyzer.models import (
    AnalysisResult,
    BottleneckCandidateResult,
    ExperimentConfig,
    ParallelAnalysisResult,
)
from ci_experiment_analyzer.parallel import (
    analyze_parallel_scenario,
    compare_parallel_scenarios,
)
from ci_experiment_analyzer.readers import read_experiment_datasets
from ci_experiment_analyzer.statistics import calculate_scenario_result


def analyze_experiment(
    config: ExperimentConfig,
) -> AnalysisResult:
    """Analyze an already validated experiment configuration."""
    datasets = read_experiment_datasets(config)

    metrics_by_id = {
        metric.id: metric
        for metric in config.metrics
    }

    scenario_results = tuple(
        calculate_scenario_result(
            dataset=datasets[scenario.id],
            metrics=config.metrics,
        )
        for scenario in config.scenarios
    )

    bottleneck_candidates: list[
        BottleneckCandidateResult
    ] = []

    for scenario_result in scenario_results:
        candidate = identify_bottleneck_candidate(
            scenario=scenario_result,
            metrics=metrics_by_id,
        )

        if candidate is not None:
            bottleneck_candidates.append(candidate)

    comparison_results = tuple(
        compare_scenarios(
            comparison=comparison,
            datasets=datasets,
            metrics=metrics_by_id,
        )
        for comparison in config.comparisons
    )

    local_total_impacts = tuple(
        impact
        for comparison_result in comparison_results
        for impact in calculate_local_total_impacts(
            comparison=comparison_result,
            metrics=metrics_by_id,
            analysis=config.analysis,
        )
    )

    parallel_analysis_results: list[
        ParallelAnalysisResult
    ] = []

    for parallel_analysis in config.parallel_analyses:
        baseline_result = analyze_parallel_scenario(
            dataset=datasets[
                parallel_analysis.baseline
            ],
            duration_metric_id=(
                parallel_analysis.duration_metric
            ),
            duration_unit="milliseconds",
        )

        candidate_result = analyze_parallel_scenario(
            dataset=datasets[
                parallel_analysis.candidate
            ],
            duration_metric_id=(
                parallel_analysis.duration_metric
            ),
            duration_unit="milliseconds",
        )

        parallel_analysis_results.append(
            compare_parallel_scenarios(
                analysis=parallel_analysis,
                baseline=baseline_result,
                candidate=candidate_result,
            )
        )

    return AnalysisResult(
        version=config.version,
        experiment=config.experiment,
        scenarios=scenario_results,
        comparisons=comparison_results,
        local_total_impacts=local_total_impacts,
        bottleneck_candidates=tuple(
            bottleneck_candidates
        ),
        parallel_analyses=tuple(
            parallel_analysis_results
        ),
    )