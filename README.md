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

The project provides an installable Python package and a working
`ci-analyzer` command-line interface.

### Implemented

- installable Python package using a `src` layout;
- YAML-based experiment configuration;
- CSV, JSON, and JSONL scenario input;
- configurable mapping of input fields to analyzer metrics;
- separate `validate` and `analyze` commands;
- configuration structure and semantic validation;
- input structure and numeric value validation;
- duration normalization to milliseconds;
- descriptive statistics for every scenario metric:
  count, median, mean, minimum, maximum, and sample standard deviation;
- baseline-versus-candidate median comparison;
- absolute and relative difference calculation;
- stable machine-readable `analysis.json` report;
- scenario-level statistics in the generated report;
- safe handling of single-observation scenarios;
- safe handling of a zero baseline median;
- minimal end-to-end example;
- frozen thesis baseline reference;
- unit and integration tests;
- GitHub Actions quality workflow;
- configurable local-versus-total impact thresholds;
- automatic comparison of local phase improvement with total pipeline
  improvement;
- detection of substantial local improvements with limited end-to-end
  impact;
- machine-readable impact classification and warnings in `analysis.json`.

### Current limitations

- comparisons currently use scenario medians;
- output is currently limited to `analysis.json`;
- longest measured phase detection is not yet implemented;
- parallel-stage and shard-planning analysis are not yet implemented.
- impact thresholds currently apply to relative median changes.

### Planned

- longest measured phase detection;
- parallel critical-path and imbalance analysis;
- Markdown and CSV reports;
- generic timing-based shard planner;
- extended thesis compatibility tests.


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

## Impact analysis thresholds

Local-versus-total impact classification is configured through the
optional `analysis` section:

```yaml
analysis:
  local_improvement_threshold_pct: 10.0
  total_impact_threshold_pct: 5.0
```

The default values are:

- `local_improvement_threshold_pct`: `10.0`;
- `total_impact_threshold_pct`: `5.0`.

Both values must be finite numbers between `0` and `100`.

The local improvement threshold defines how much a duration metric with
`role: phase` must improve before the local improvement is considered
substantial.

The total impact threshold defines how much a duration metric with
`role: total` must improve before the end-to-end pipeline impact is
considered meaningful.

Impact analysis applies only to duration metrics that participate in the
same configured comparison:

- the local metric must have `role: phase`;
- the total pipeline metric must have `role: total`.

Comparison differences are calculated as:

```text
candidate - baseline
```

For duration metrics, negative relative differences represent
improvements and positive relative differences represent regressions.


## Analysis report

The `analyze` command writes a machine-readable report to:

```text
<output-directory>/analysis.json
```

The report contains:

- configuration version and experiment metadata;
- descriptive statistics for every configured scenario metric;
- configured baseline-versus-candidate comparisons;
- local-versus-total impact classifications and optional warnings.

Each scenario metric contains:

- `count`;
- `median`;
- `mean`;
- `minimum`;
- `maximum`;
- `standard_deviation`.

Duration values are normalized to milliseconds before statistics and
comparisons are calculated.

Sample standard deviation is used. A metric containing one observation
has the following result:

```json
{
  "standard_deviation": 0.0
}
```

Comparison differences are calculated as:

```text
candidate - baseline
```

For duration metrics:

- a negative value normally represents an improvement;
- a positive value normally represents a regression;
- zero means that the median did not change.

When the baseline median is zero, relative change cannot be calculated.
The report represents this as:

```json
{
  "relative_difference_percent": null
}
```
### Local-versus-total impact

The report contains a `local_vs_total_impacts` section for duration
metrics with `phase` and `total` roles that participate in the same
comparison.

Example:

```json
{
  "local_vs_total_impacts": [
    {
      "comparison": "cache-impact",
      "phase_metric": "install_duration",
      "total_metric": "total_duration",
      "phase_relative_difference_percent": -25.0,
      "total_relative_difference_percent": -11.11111111111111,
      "local_improvement_threshold_pct": 10.0,
      "total_impact_threshold_pct": 5.0,
      "substantial_local_improvement": true,
      "limited_total_improvement": false,
      "limited_end_to_end_impact": false,
      "warning": null
    }
  ]
}
```

The classification fields have the following meaning:

- `substantial_local_improvement` indicates whether the local phase
  improvement reached the configured local threshold;
- `limited_total_improvement` indicates whether total pipeline
  improvement remained below the configured total threshold;
- `limited_end_to_end_impact` is `true` only when the local improvement
  is substantial and the total improvement remains limited;
- `warning` contains an interpretation message when limited end-to-end
  impact is detected.

When a relative change cannot be calculated because the corresponding
baseline median is zero, the affected classification is represented as
`null`.


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
