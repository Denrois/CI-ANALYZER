"""Coordinate configured CI experiment analysis."""

from ci_experiment_analyzer.comparisons import compare_scenarios
from ci_experiment_analyzer.impact import calculate_local_total_impacts
from ci_experiment_analyzer.models import (
    AnalysisResult,
    ExperimentConfig,
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
        )
    )

    return AnalysisResult(
        version=config.version,
        experiment=config.experiment,
        scenarios=scenario_results,
        comparisons=comparison_results,
        local_total_impacts=local_total_impacts,
    )