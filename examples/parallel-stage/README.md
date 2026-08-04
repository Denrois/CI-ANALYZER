# Parallel Stage Analysis Example

This example demonstrates analysis of parallel CI branches, such as test
shards, matrix jobs, or other tasks that run concurrently inside one
pipeline stage.

It compares two scenarios:

- `baseline`, where branch durations are uneven;
- `timing-based`, where branch durations are evenly balanced.

The example demonstrates:

- grouping branch measurements by CI run;
- validation of branch identifiers;
- calculation of per-run parallel-stage metrics;
- aggregation of metrics across repeated CI runs;
- baseline-versus-candidate comparison;
- branch-count consistency reporting;
- detection of slowest branches and ties;
- JSON, CSV, and Markdown report generation.

## Input data

The example contains two CSV datasets:

```text
data/
|-- baseline.csv
`-- timing-based.csv
```

Each CSV row represents one measured parallel branch.

Rows sharing the same `workflow_run_id` belong to the same CI run.

Example:

```csv
workflow_run_id,shard_id,shard_duration_seconds
baseline-1,shard-1,40
baseline-1,shard-2,20
baseline-2,shard-1,30
baseline-2,shard-2,10
```

The configured record mapping is:

```yaml
record_mapping:
  run_id: workflow_run_id
  branch_id: shard_id
```

The combination of `run_id` and `branch_id` must be unique within one
scenario.

The same branch identifier may be reused in different CI runs.

For example, these pairs are valid:

```text
baseline-1, shard-1
baseline-2, shard-1
```

These pairs are invalid because they are duplicated inside the same run:

```text
baseline-1, shard-1
baseline-1, shard-1
```

## Parallel branch metric

The measured duration metric uses `role: parallel_branch`:

```yaml
metrics:
  - id: shard_duration
    field: shard_duration_seconds
    type: duration
    unit: seconds
    role: parallel_branch
```

The source values are expressed in seconds.

All generated duration values are normalized to milliseconds before
parallel-run calculations and comparisons are performed.

For example:

```text
40 seconds -> 40000 milliseconds
```

## Parallel analysis configuration

Parallel-stage analysis is configured separately from ordinary metric
comparisons:

```yaml
comparisons: []

parallel_analyses:
  - id: test-sharding-balance
    baseline: baseline
    candidate: timing-based
    duration_metric: shard_duration
```

The configuration identifies:

- the parallel analysis ID;
- the baseline scenario;
- the candidate scenario;
- the configured branch-duration metric.

## Validate

Run the command from the repository root:

```powershell
ci-analyzer validate `
  --config examples/parallel-stage/experiment.yaml
```

The same command on one line:

```powershell
ci-analyzer validate --config examples/parallel-stage/experiment.yaml
```

Expected output:

```text
Configuration and data are valid: examples\parallel-stage\experiment.yaml
```

The exact path separators may differ between Windows and Unix-like
systems.

## Analyze

Run the analysis from the repository root:

```powershell
ci-analyzer analyze `
  --config examples/parallel-stage/experiment.yaml `
  --output .tmp/parallel-stage-report
```

The same command on one line:

```powershell
ci-analyzer analyze --config examples/parallel-stage/experiment.yaml --output .tmp/parallel-stage-report
```

Expected output:

```text
Analysis written to:
- .tmp\parallel-stage-report\analysis.json
- .tmp\parallel-stage-report\summary.csv
- .tmp\parallel-stage-report\report.md
```

The command creates:

```text
.tmp/parallel-stage-report/
|-- analysis.json
|-- summary.csv
`-- report.md
```

The files serve different purposes:

- `analysis.json` preserves complete run-level and aggregated analysis
  data;
- `summary.csv` contains a flat table of derived comparison metrics;
- `report.md` provides a human-readable parallel-stage report.

## Calculated run metrics

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
- the identifiers of the slowest branches;
- whether several branches are tied for the maximum duration.

An `imbalance_ratio` of `1.0` represents equal branch durations.

Increasing values indicate greater imbalance.

When all branch durations are zero, the analyzer reports an imbalance
ratio of `1.0`, representing a neutral and fully balanced result.

The term `critical_path_duration` refers only to the longest measured
branch inside the configured parallel stage.

It does not represent a reconstructed critical path of the complete CI
pipeline.

## Baseline runs

The baseline input contains two CI runs:

```text
baseline-1: 40 s, 20 s
baseline-2: 30 s, 10 s
```

### `baseline-1`

Input branch durations:

```text
shard-1: 40 seconds
shard-2: 20 seconds
```

Calculated values:

```text
branch count: 2
critical path duration: 40 seconds
minimum branch duration: 20 seconds
mean branch duration: 30 seconds
spread: 20 seconds
imbalance ratio: 40 / 30 = 1.333333...
slowest branch: shard-1
slowest-branch tie: false
```

### `baseline-2`

Input branch durations:

```text
shard-1: 30 seconds
shard-2: 10 seconds
```

Calculated values:

```text
branch count: 2
critical path duration: 30 seconds
minimum branch duration: 10 seconds
mean branch duration: 20 seconds
spread: 20 seconds
imbalance ratio: 30 / 20 = 1.5
slowest branch: shard-1
slowest-branch tie: false
```

The run metrics can be summarized as:

| Run | Branches | Critical path | Minimum | Mean | Spread | Imbalance ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `baseline-1` | 2 | 40 s | 20 s | 30 s | 20 s | approximately 1.3333 |
| `baseline-2` | 2 | 30 s | 10 s | 20 s | 20 s | 1.5 |

The baseline scenario medians are:

```text
critical path duration: 35 seconds
spread: 20 seconds
imbalance ratio: 17 / 12, approximately 1.4167
```

## Timing-based runs

The candidate input contains two CI runs:

```text
timing-based-1: 30 s, 30 s
timing-based-2: 20 s, 20 s
```

### `timing-based-1`

Input branch durations:

```text
shard-1: 30 seconds
shard-2: 30 seconds
```

Calculated values:

```text
branch count: 2
critical path duration: 30 seconds
minimum branch duration: 30 seconds
mean branch duration: 30 seconds
spread: 0 seconds
imbalance ratio: 1.0
slowest branches: shard-1, shard-2
slowest-branch tie: true
```

### `timing-based-2`

Input branch durations:

```text
shard-1: 20 seconds
shard-2: 20 seconds
```

Calculated values:

```text
branch count: 2
critical path duration: 20 seconds
minimum branch duration: 20 seconds
mean branch duration: 20 seconds
spread: 0 seconds
imbalance ratio: 1.0
slowest branches: shard-1, shard-2
slowest-branch tie: true
```

The run metrics can be summarized as:

| Run | Branches | Critical path | Minimum | Mean | Spread | Imbalance ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `timing-based-1` | 2 | 30 s | 30 s | 30 s | 0 s | 1.0 |
| `timing-based-2` | 2 | 20 s | 20 s | 20 s | 0 s | 1.0 |

Both candidate runs contain tied slowest branches because all measured
branches have equal durations.

The candidate scenario medians are:

```text
critical path duration: 25 seconds
spread: 0 seconds
imbalance ratio: 1.0
```

## Expected comparison

Scenario comparisons use median values.

Differences are calculated as:

```text
candidate - baseline
```

Expected normalized values:

| Metric | Baseline median | Candidate median | Absolute difference | Relative difference |
| --- | ---: | ---: | ---: | ---: |
| `critical_path_duration` | 35000 ms | 25000 ms | -10000 ms | approximately -28.57% |
| `spread` | 20000 ms | 0 ms | -20000 ms | -100% |
| `imbalance_ratio` | approximately 1.4167 | 1.0 | approximately -0.4167 | approximately -29.41% |

For these metrics, negative changes normally represent an improvement:

- a shorter critical branch reduces parallel-stage completion time;
- a smaller spread indicates more even branch durations;
- an imbalance ratio closer to `1.0` indicates better load balance.

The expected exact comparison values are:

```text
critical path relative difference:
-10000 / 35000 * 100 = approximately -28.5714%

spread relative difference:
-20000 / 20000 * 100 = -100%

imbalance absolute difference:
1 - 17/12 = -5/12, approximately -0.4167

imbalance relative difference:
(-5/12) / (17/12) * 100
= -500/17
= approximately -29.4118%
```

## Branch-count consistency

Both scenarios contain exactly two branches in every analyzed CI run.

The generated result therefore contains:

```json
{
  "branch_count": {
    "minimum": 2,
    "maximum": 2,
    "consistent": true
  }
}
```

The analyzer records branch-count consistency separately for the baseline
and candidate scenarios.

When branch counts differ between runs, the report contains different
minimum and maximum values:

```json
{
  "branch_count": {
    "minimum": 2,
    "maximum": 3,
    "consistent": false
  }
}
```

An inconsistent branch count is also included in the warnings section of
the Markdown report.

## JSON report

The complete structured result is written to:

```text
.tmp/parallel-stage-report/analysis.json
```

The `parallel_analyses` section contains:

- the analysis ID;
- the configured source duration metric;
- baseline run-level results;
- candidate run-level results;
- aggregated descriptive statistics;
- branch-count ranges and consistency;
- derived comparison metrics.

A simplified structure is:

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
        }
      },
      "candidate": {
        "scenario": "timing-based",
        "duration_unit": "milliseconds",
        "branch_count": {
          "minimum": 2,
          "maximum": 2,
          "consistent": true
        }
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

## CSV summary

The flat comparison summary is written to:

```text
.tmp/parallel-stage-report/summary.csv
```

It contains one row for each derived comparison metric:

```text
critical_path_duration
spread
imbalance_ratio
```

For every row:

```text
analysis_type = parallel_analysis
analysis_id = test-sharding-balance
baseline_scenario = baseline
candidate_scenario = timing-based
source_metric_id = shard_duration
```

A simplified CSV representation is:

```csv
analysis_type,analysis_id,baseline_scenario,candidate_scenario,source_metric_id,metric_id,unit,baseline_median,candidate_median,absolute_difference,relative_difference_percent
parallel_analysis,test-sharding-balance,baseline,timing-based,shard_duration,critical_path_duration,milliseconds,35000.0,25000.0,-10000.0,-28.57142857142857
parallel_analysis,test-sharding-balance,baseline,timing-based,shard_duration,spread,milliseconds,20000.0,0.0,-20000.0,-100.0
parallel_analysis,test-sharding-balance,baseline,timing-based,shard_duration,imbalance_ratio,ratio,1.4166666666666665,1.0,-0.4166666666666665,-29.411764705882344
```

`source_metric_id` identifies the configured branch-duration metric.

`metric_id` identifies the derived parallel-stage metric being compared.

## Markdown report

The human-readable report is written to:

```text
.tmp/parallel-stage-report/report.md
```

It contains:

- experiment overview;
- scenario descriptive statistics;
- parallel analysis identification;
- baseline and candidate branch-count ranges;
- branch-count consistency;
- median critical-path duration;
- median spread;
- median imbalance ratio;
- derived comparison results;
- individual run metrics;
- slowest branches;
- slowest-branch ties;
- warnings;
- interpretation limitations.

Numbers are formatted for readability.

For example, the full imbalance-ratio value:

```text
1.4166666666666665
```

is displayed in Markdown as:

```text
1.416667
```

The Markdown report also makes clear that the reported critical path
belongs only to the configured parallel stage and does not represent the
dependency graph of the complete CI pipeline.