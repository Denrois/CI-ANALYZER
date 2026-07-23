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

**Early functional prototype**

The project already provides an installable Python package and a working
`ci-analyzer` command-line interface.

### Implemented

- installable Python package using a `src` layout;
- YAML-based experiment configuration;
- CSV, JSON, and JSONL scenario input;
- configurable mapping of CSV columns to analyzer metrics;
- separate `validate` and `analyze` commands;
- configuration structure and semantic validation;
- CSV header and value validation;
- baseline-versus-candidate median comparison;
- absolute and relative difference calculation;
- duration normalization to milliseconds;
- JSON analysis report;
- minimal end-to-end example;
- frozen thesis baseline reference;
- unit and integration tests.

### Current limitations

- comparisons currently use medians;
- output is currently limited to `analysis.json`;
- the analyzer does not yet calculate full descriptive statistics;
- parallel-stage and shard-planning analysis are not yet implemented.

### Planned

- full descriptive statistics;
- local-phase versus total-impact analysis;
- longest measured phase detection;
- parallel critical-path and imbalance analysis;
- Markdown and CSV reports;
- generic timing-based shard planner;
- extended thesis compatibility tests.

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


## Quick start

The project requires Python 3.13.

Install the package and development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Verify the installed CLI:

```powershell
ci-analyzer --version
```

Validate the included minimal experiment:

```powershell
ci-analyzer validate --config examples/minimal/experiment.yaml
```

Run the analysis:

```powershell
ci-analyzer analyze `
  --config examples/minimal/experiment.yaml `
  --output .tmp/minimal-report
```

The same command on one line:

```powershell
ci-analyzer analyze --config examples/minimal/experiment.yaml --output .tmp/minimal-report
```

The generated report is written to:

```text
.tmp/minimal-report/analysis.json
```

Duration metrics are normalized to milliseconds in the generated report,
regardless of whether their source unit is configured as milliseconds,
seconds, or minutes.

## Supported input formats

The analyzer currently supports three scenario input formats:

- CSV;
- JSON;
- JSONL.

The source format is selected independently for each scenario in the YAML configuration:

```yaml
scenarios:
  - id: baseline
    source:
      format: json
      path: data/baseline.json
```

### CSV

CSV input must contain a header row:

```csv
run_id,total_seconds
run-1,50.0
run-2,54.0
```

### JSON

JSON input must contain a top-level array of objects:

```json
[
  {
    "run_id": "run-1",
    "total_seconds": 50.0
  },
  {
    "run_id": "run-2",
    "total_seconds": 54.0
  }
]
```

### JSONL

JSONL input must contain one JSON object per non-empty line:

```jsonl
{"run_id": "run-1", "total_seconds": 50.0}
{"run_id": "run-2", "total_seconds": 54.0}
```

All three formats use the same configurable field mapping, validation,
normalization, statistical calculations, comparisons, and report generation.

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
