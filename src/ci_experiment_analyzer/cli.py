"""Command-line interface for CI Experiment Analyzer."""

import argparse
from collections.abc import Sequence

from ci_experiment_analyzer import __version__


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

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line interface."""
    parser = build_parser()
    parser.parse_args(argv)

    return 0