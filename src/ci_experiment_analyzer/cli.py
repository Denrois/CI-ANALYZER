"""Command-line interface for CI Experiment Analyzer."""

import argparse
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import cast

from ci_experiment_analyzer import __version__
from ci_experiment_analyzer.comparisons import compare_scenarios
from ci_experiment_analyzer.config import load_config
from ci_experiment_analyzer.errors import (
    ConfigValidationError,
    DataValidationError,
)
from ci_experiment_analyzer.readers import read_experiment_datasets
from ci_experiment_analyzer.reports import write_analysis_json
from ci_experiment_analyzer.validation import validate_config

CommandHandler = Callable[[argparse.Namespace], int]


def _run_validate(args: argparse.Namespace) -> int:
    """Execute the validate command."""
    config_path = cast(Path, args.config)

    config = load_config(config_path)
    validate_config(config)
    read_experiment_datasets(config)

    print(f"Configuration and data are valid: {config_path}")

    return 0


def _run_analyze(args: argparse.Namespace) -> int:
    """Execute the analyze command."""
    config_path = cast(Path, args.config)
    output_directory = cast(Path, args.output)

    config = load_config(config_path)
    validate_config(config)

    datasets = read_experiment_datasets(config)

    metrics_by_id = {
        metric.id: metric
        for metric in config.metrics
    }

    comparison_results = tuple(
        compare_scenarios(
            comparison=comparison,
            datasets=datasets,
            metrics=metrics_by_id,
        )
        for comparison in config.comparisons
    )

    report_path = write_analysis_json(
        config=config,
        comparison_results=comparison_results,
        output_directory=output_directory,
    )

    print(f"Analysis written to {report_path}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    """Create and configure the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="ci-analyzer",
        description=(
            "Analyze CI pipeline optimization experiments "
            "and generate reproducible reports."
        ),
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate an experiment configuration.",
    )
    validate_parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to the experiment YAML configuration.",
    )
    validate_parser.set_defaults(handler=_run_validate)

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze configured experiment scenarios.",
    )
    analyze_parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to the experiment YAML configuration.",
    )
    analyze_parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Directory where analysis.json will be written.",
    )
    analyze_parser.set_defaults(handler=_run_analyze)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line interface."""
    parser = build_parser()
    args = parser.parse_args(argv)

    handler = cast(CommandHandler, args.handler)

    try:
        return handler(args)
    except (ConfigValidationError, DataValidationError) as error:
        parser.error(str(error))