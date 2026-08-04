# Minimal CSV Example

This example demonstrates the smallest supported CI experiment analysis.

It compares two scenarios:

- `baseline`;
- `optimized`.

The input data is stored in CSV files. Column names are mapped to analyzer
metrics through `experiment.yaml`.

The example demonstrates:

- configuration and input validation;
- duration normalization;
- scenario descriptive statistics;
- baseline-versus-candidate comparison;
- local-versus-total impact classification;
- bottleneck candidate detection;
- JSON, CSV, and Markdown report generation.

## Validate

Run the command from the repository root:

```powershell
ci-analyzer validate `
  --config examples/minimal/experiment.yaml
```

The same command on one line:

```powershell
ci-analyzer validate --config examples/minimal/experiment.yaml
```

Expected output:

```text
Configuration and data are valid: examples\minimal\experiment.yaml
```

The exact path separators may differ between Windows and Unix-like
systems.

## Analyze

Run the analysis from the repository root:

```powershell
ci-analyzer analyze `
  --config examples/minimal/experiment.yaml `
  --output .tmp/minimal-report
```

The same command on one line:

```powershell
ci-analyzer analyze --config examples/minimal/experiment.yaml --output .tmp/minimal-report
```

Expected output:

```text
Analysis written to:
- .tmp\minimal-report\analysis.json
- .tmp\minimal-report\summary.csv
- .tmp\minimal-report\report.md
```

The command creates:

```text
.tmp/minimal-report/
|-- analysis.json
|-- summary.csv
`-- report.md
```

The files serve different purposes:

- `analysis.json` preserves the complete structured analysis;
- `summary.csv` contains a flat table of configured comparison metrics;
- `report.md` provides a human-readable experiment report.

## Input data

The example contains two CSV datasets:

```text
data/
|-- baseline.csv
`-- optimized.csv
```

Each row represents one CI run.

The configured field mapping identifies the run ID:

```yaml
record_mapping:
  run_id: run_id
```

The experiment defines two duration metrics:

```yaml
metrics:
  - id: install_duration
    field: install_seconds
    type: duration
    unit: seconds
    role: phase

  - id: total_duration
    field: total_seconds
    type: duration
    unit: seconds
    role: total
```

`install_duration` represents one measured pipeline phase.

`total_duration` represents the complete measured pipeline duration.

## Duration normalization

Duration metrics are normalized to milliseconds before statistics and
comparisons are calculated.

The supported duration units are:

- `milliseconds`;
- `seconds`;
- `minutes`.

The source CSV files in this example contain values in seconds. Generated
reports contain the corresponding normalized values in milliseconds.

For example:

```text
12 seconds -> 12000 milliseconds
```

## Expected scenario statistics

The example contains five observations for each scenario.

Expected medians:

| Metric | Baseline | Optimized | Absolute difference | Relative difference |
| --- | ---: | ---: | ---: | ---: |
| `install_duration` | 12000 ms | 9000 ms | -3000 ms | -25.0% |
| `total_duration` | 54000 ms | 48000 ms | -6000 ms | approximately -11.11% |

The difference is calculated as:

```text
candidate - baseline
```

For duration metrics:

- a negative value normally represents an improvement;
- a positive value normally represents a regression;
- zero means that the median did not change.

The generated reports also contain:

- observation count;
- arithmetic mean;
- minimum;
- maximum;
- sample standard deviation.

## JSON report

The complete structured result is written to:

```text
.tmp/minimal-report/analysis.json
```

The report contains:

- experiment metadata;
- scenario statistics;
- configured comparisons;
- local-versus-total impact classification;
- bottleneck candidates;
- parallel analyses.

The final `parallel_analyses` section is empty because this example does
not configure parallel-stage analysis:

```json
{
  "parallel_analyses": []
}
```

## CSV summary

The flat comparison summary is written to:

```text
.tmp/minimal-report/summary.csv
```

It contains one row for each configured comparison metric.

Expected metric rows:

```text
install_duration
total_duration
```

A simplified representation is:

```csv
analysis_type,analysis_id,baseline_scenario,candidate_scenario,source_metric_id,metric_id,unit,baseline_median,candidate_median,absolute_difference,relative_difference_percent
comparison,cache-impact,baseline,optimized,install_duration,install_duration,milliseconds,12000.0,9000.0,-3000.0,-25.0
comparison,cache-impact,baseline,optimized,total_duration,total_duration,milliseconds,54000.0,48000.0,-6000.0,-11.11111111111111
```

For an ordinary comparison, `source_metric_id` and `metric_id` refer to
the same configured metric.

## Markdown report

The human-readable report is written to:

```text
.tmp/minimal-report/report.md
```

It contains:

- experiment overview;
- scenario statistics;
- comparison tables;
- local-versus-total impact classification;
- bottleneck candidates;
- warnings;
- interpretation limitations.

Numbers are formatted for readability. For example, the full JSON value:

```text
-11.11111111111111
```

is displayed in Markdown as:

```text
-11.111111%
```

## Local-versus-total impact

The example uses the following impact thresholds:

```yaml
analysis:
  local_improvement_threshold_pct: 10.0
  total_impact_threshold_pct: 5.0
```

The `install_duration` metric has `role: phase` and improves from a median
of `12000.0` milliseconds to `9000.0` milliseconds:

```text
relative difference: -25.0%
```

The `total_duration` metric has `role: total` and improves from a median
of `54000.0` milliseconds to `48000.0` milliseconds:

```text
relative difference: approximately -11.11%
```

The local improvement exceeds the configured `10.0%` threshold.

The total pipeline improvement also exceeds the configured `5.0%`
threshold.

The expected classification is therefore:

```json
{
  "substantial_local_improvement": true,
  "limited_total_improvement": false,
  "limited_end_to_end_impact": false,
  "warning": null
}
```

This result means that the local optimization is accompanied by a
meaningful improvement in the measured total pipeline duration.

## Bottleneck candidates

The minimal experiment contains one measured duration metric with
`role: phase`:

```text
install_duration
```

The `total_duration` metric is excluded because it has `role: total` and
represents the complete pipeline duration rather than an individual
phase.

Expected bottleneck candidates:

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

Because each scenario contains only one measured duration phase, that
phase is selected as the bottleneck candidate in both scenarios.

The result is described as a candidate rather than a confirmed
bottleneck because the analyzer compares measured phase durations without
reconstructing the dependency graph of the complete CI pipeline.