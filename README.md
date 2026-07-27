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
- automatic identification of the longest measured duration phase in each
  scenario;
- deterministic handling of tied bottleneck candidates;
- machine-readable bottleneck candidates in `analysis.json`;
- automatic comparison of local phase improvement with total pipeline
  improvement;
- detection of substantial local improvements with limited end-to-end
  impact;
- machine-readable impact classification and warnings in `analysis.json`;
- configurable parallel branch identification through `run_id` and
  `branch_id` field mappings;
- grouping of parallel branch records by CI run;
- validation of duplicate branch identifiers within the same run;
- per-run parallel-stage metrics:
  critical-path duration, minimum and mean branch duration, spread, and
  imbalance ratio;
- deterministic reporting of slowest branches and tied slowest branches;
- aggregated parallel-stage statistics across multiple CI runs;
- detection of inconsistent branch counts between runs;
- baseline-versus-candidate comparison of critical-path duration, spread,
  and imbalance ratio;
- machine-readable parallel-stage analysis in `analysis.json`;
- end-to-end parallel-stage example and CLI integration tests.

### Current limitations

- comparisons currently use scenario medians;
- output is currently limited to `analysis.json`;
- bottleneck detection considers measured duration metrics with
  `role: phase` independently for each scenario;
- parallel-stage analysis expects one input record per measured branch;
- every parallel branch must have a unique `(run_id, branch_id)` pair
  within its scenario;
- parallel critical-path duration represents the longest measured branch
  inside one parallel stage and does not reconstruct the dependency graph
  or critical path of the complete CI pipeline;
- automatic shard planning is not yet implemented;
- impact thresholds currently apply to relative median changes.

### Planned

- Markdown and CSV reports;
- generic timing-based shard planner;
- extended thesis compatibility tests.


## Quick start

The generated report is written to:

```text
.tmp/minimal-report/analysis.json
```

Run the included parallel-stage example:

```powershell
ci-analyzer validate `
  --config examples/parallel-stage/experiment.yaml
```

Run the analysis:

```powershell
ci-analyzer analyze `
  --config examples/parallel-stage/experiment.yaml `
  --output .tmp/parallel-stage-report
```

The same analysis command on one line:

```powershell
ci-analyzer analyze --config examples/parallel-stage/experiment.yaml --output .tmp/parallel-stage-report
```

The generated parallel-stage report is written to:

```text
.tmp/parallel-stage-report/analysis.json
```

See
[`examples/parallel-stage/README.md`](examples/parallel-stage/README.md)
for the input structure, expected calculations, and report semantics.

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
- local-versus-total impact classifications and optional warnings;
- bottleneck candidates for scenarios containing measured duration phases;
- parallel-stage run metrics, aggregated scenario statistics, and
  baseline-versus-candidate comparisons.

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


### Bottleneck candidates

The report contains a `bottleneck_candidates` section that identifies the
longest measured duration phase in each scenario.

Only metrics satisfying both conditions participate:

- the metric type is `duration`;
- the metric role is `phase`.

Metrics with `role: total` are excluded because total pipeline duration is
not an individual phase. Generic `number` metrics are also excluded.

Example:

```json
{
  "bottleneck_candidates": [
    {
      "scenario": "baseline",
      "phase_metrics": [
        "install_duration"
      ],
      "median": 12000.0,
      "unit": "milliseconds",
      "is_tie": false
    },
    {
      "scenario": "optimized",
      "phase_metrics": [
        "install_duration"
      ],
      "median": 9000.0,
      "unit": "milliseconds",
      "is_tie": false
    }
  ]
}
```

The candidate is selected using the largest phase median in the scenario.

The result is described as a candidate rather than a confirmed bottleneck
because the analyzer currently compares measured phase durations without
reconstructing pipeline dependencies or a parallel critical path.

When several phase metrics have equal maximum medians, all of them are
reported in their configured order:

```json
{
  "scenario": "baseline",
  "phase_metrics": [
    "build_duration",
    "test_duration"
  ],
  "median": 20000.0,
  "unit": "milliseconds",
  "is_tie": true
}
```

A scenario without duration metrics using `role: phase` does not produce a
bottleneck candidate.

### Parallel-stage analysis

The report contains a `parallel_analyses` section for configured
parallel-stage comparisons.

Parallel input uses two record identifiers:

```yaml
record_mapping:
  run_id: workflow_run_id
  branch_id: shard_id
```

Each input record represents one measured parallel branch. Records sharing
the same `run_id` belong to the same CI run.

The combination of `run_id` and `branch_id` must be unique within a
scenario. The same branch identifier may be reused in different runs.

A parallel branch duration metric must use:

```yaml
metrics:
  - id: shard_duration
    field: shard_duration_seconds
    type: duration
    unit: seconds
    role: parallel_branch
```

Parallel comparison is configured separately from ordinary metric
comparisons:

```yaml
comparisons: []

parallel_analyses:
  - id: test-sharding-balance
    baseline: baseline
    candidate: timing-based
    duration_metric: shard_duration
```

For every grouped CI run, the analyzer calculates:

```text
critical_path_duration = maximum branch duration
minimum_branch_duration = minimum branch duration
mean_branch_duration = arithmetic mean of branch durations
spread = maximum branch duration - minimum branch duration
imbalance_ratio = maximum branch duration / mean branch duration
```

The run result also contains:

- the number of measured branches;
- the slowest branch identifiers;
- whether several branches are tied for the maximum duration.

An imbalance ratio of `1.0` represents equal branch durations. Increasing
values indicate greater imbalance.

When every branch duration is zero, the imbalance ratio is reported as
`1.0`, representing a neutral and fully balanced result.

The term `critical_path_duration` refers only to the longest measured
branch inside the configured parallel stage. It does not represent a
reconstructed critical path of the complete pipeline.

Run-level values are aggregated separately for the baseline and candidate
scenarios. The following descriptive statistics are calculated:

- `count`;
- `median`;
- `mean`;
- `minimum`;
- `maximum`;
- `standard_deviation`.

The report also records whether every analyzed run used the same number of
branches:

```json
{
  "branch_count": {
    "minimum": 2,
    "maximum": 2,
    "consistent": true
  }
}
```

The scenario comparison uses median values for:

- `critical_path_duration`;
- `spread`;
- `imbalance_ratio`.

Differences use the same convention as ordinary comparisons:

```text
candidate - baseline
```

Negative changes normally represent an improvement:

- a shorter critical branch reduces parallel-stage completion time;
- a smaller spread represents more even branch durations;
- a lower imbalance ratio represents better balance when it moves closer
  to `1.0`.

A simplified report structure looks like this:

```json
{
  "parallel_analyses": [
    {
      "id": "test-sharding-balance",
      "duration_metric": "shard_duration",
      "baseline": {
        "scenario": "baseline",
        "duration_unit": "milliseconds",
        "branch_count": {
          "minimum": 2,
          "maximum": 2,
          "consistent": true
        },
        "runs": [
          {
            "run_id": "baseline-1",
            "branch_count": 2,
            "critical_path_duration": 40000.0,
            "minimum_branch_duration": 20000.0,
            "mean_branch_duration": 30000.0,
            "spread": 20000.0,
            "imbalance_ratio": 1.3333333333333333,
            "slowest_branches": [
              "shard-1"
            ],
            "is_slowest_tie": false
          }
        ]
      },
      "candidate": {
        "scenario": "timing-based",
        "duration_unit": "milliseconds"
      },
      "metrics": [
        {
          "id": "critical_path_duration",
          "unit": "milliseconds",
          "baseline_median": 35000.0,
          "candidate_median": 25000.0,
          "absolute_difference": -10000.0,
          "relative_difference_percent": -28.57142857142857
        },
        {
          "id": "spread",
          "unit": "milliseconds",
          "baseline_median": 20000.0,
          "candidate_median": 0.0,
          "absolute_difference": -20000.0,
          "relative_difference_percent": -100.0
        },
        {
          "id": "imbalance_ratio",
          "unit": "ratio",
          "baseline_median": 1.4166666666666665,
          "candidate_median": 1.0,
          "absolute_difference": -0.4166666666666665,
          "relative_difference_percent": -29.411764705882344
        }
      ]
    }
  ]
}
```

All configured duration values are normalized to milliseconds before
parallel-run calculations are performed.

## Repository structure

```text
ci-experiment-analyzer/
|-- docs/                   # Project documentation
|-- examples/               # Example experiments and input data
|   |-- minimal/
|   `-- parallel-stage/
|-- reference/              # Original thesis snapshot and expected results
`-- tests/                  # Automated tests
```

## Development approach

Each milestone should leave the project in a working and testable state:

```text
small working increment
-> tests
-> commit
-> push
-> next increment
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
