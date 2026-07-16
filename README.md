# CI Experiment Analyzer

A Python CLI tool for reproducible analysis of CI pipeline optimization experiments.

## Overview

CI Experiment Analyzer is intended to help engineers evaluate whether changes to a CI pipeline produce meaningful and repeatable improvements.

The project will support:

* loading experimental CI metrics;
* comparing baseline and candidate scenarios;
* calculating descriptive statistics;
* separating local phase improvements from total pipeline impact;
* identifying the longest measured phase;
* analyzing parallel jobs and sharding balance;
* generating JSON, CSV, and Markdown reports.

## Project origin

This project originated from a diploma thesis on CI/CD pipeline optimization.

The original implementation analyzed a fixed set of thesis experiments, including dependency caching, Docker build caching, and timing-based test sharding.

The goal of this repository is to redesign that prototype into a configurable and reusable Python CLI tool that can evaluate CI optimization experiments across different projects.

## Project status

The project is currently in the initial development stage.

The repository structure and development baseline are being prepared before the first functional version of the analyzer is implemented.

## Planned features

* configuration-driven experiment analysis;
* CSV, JSON, and JSONL input formats;
* baseline versus candidate comparisons;
* descriptive statistics;
* local versus total impact analysis;
* longest measured phase detection;
* parallel stage critical-path analysis;
* sharding balance analysis;
* JSON, CSV, and Markdown reports;
* generic work-item shard planner;
* automated tests and GitHub Actions.

## Repository structure

```text
ci-experiment-analyzer/
├── docs/        # Project documentation
├── examples/    # Example experiments and input data
├── reference/   # Original thesis snapshot and expected results
└── tests/       # Automated tests
```

## Development approach

Each milestone should leave the project in a working and testable state:

```text
small working increment
→ tests
→ commit
→ push
→ next increment
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
