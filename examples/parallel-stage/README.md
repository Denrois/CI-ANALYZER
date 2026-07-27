# Parallel Stage Analysis Example

This example demonstrates analysis of parallel CI branches, such as test
shards or matrix jobs.

It compares two scenarios:

- `baseline`, where branch durations are uneven;
- `timing-based`, where branch durations are evenly balanced.

Each CSV row represents one parallel branch. Rows sharing the same
`workflow_run_id` belong to the same CI run.

## Input structure

The configured record mapping is:

```yaml
record_mapping:
  run_id: workflow_run_id
  branch_id: shard_id
```

The measured duration metric uses the `parallel_branch` role:

```yaml
metrics:
  - id: shard_duration
    field: shard_duration_seconds
    type: duration
    unit: seconds
    role: parallel_branch
```

The scenarios are compared through a configured parallel analysis:

```yaml
parallel_analyses:
  - id: test-sharding-balance
    baseline: baseline
    candidate: timing-based
    duration_metric: shard_duration
```

## Validate

Execute from the repository root:

```powershell
ci-analyzer validate `
  --config examples/parallel-stage/experiment.yaml
```

The same command on one line:

```powershell
ci-analyzer validate --config examples/parallel-stage/experiment.yaml
```

## Analyze

```powershell
ci-analyzer analyze `
  --config examples/parallel-stage/experiment.yaml `
  --output .tmp/parallel-stage-report
```

The same command on one line:

```powershell
ci-analyzer analyze --config examples/parallel-stage/experiment.yaml --output .tmp/parallel-stage-report
```

The generated report is written to:

```text
.tmp/parallel-stage-report/analysis.json
```

## Calculated run metrics

For every CI run, the analyzer calculates:

- `critical_path_duration`: the maximum branch duration;
- `minimum_branch_duration`: the minimum branch duration;
- `mean_branch_duration`: the arithmetic mean of branch durations;
- `spread`: maximum duration minus minimum duration;
- `imbalance_ratio`: maximum duration divided by mean duration;
- the slowest branch or tied slowest branches.

An `imbalance_ratio` of `1.0` represents perfectly equal branch
durations. Larger values indicate increasing imbalance.

The critical path in this report refers to the longest branch inside the
measured parallel stage. It does not reconstruct the critical path of the
complete CI pipeline.

## Baseline runs

The baseline input contains:

```text
baseline-1: 40 s, 20 s
baseline-2: 30 s, 10 s
```

The calculated run metrics are:

| Run | Critical path | Mean | Spread | Imbalance ratio |
|---|---:|---:|---:|---:|
| `baseline-1` | 40 s | 30 s | 20 s | 1.3333 |
| `baseline-2` | 30 s | 20 s | 20 s | 1.5 |

The scenario medians are:

```text
critical path duration: 35 seconds
spread: 20 seconds
imbalance ratio: 17 / 12, approximately 1.4167
```

## Timing-based runs

The candidate input contains:

```text
timing-based-1: 30 s, 30 s
timing-based-2: 20 s, 20 s
```

The calculated run metrics are:

| Run | Critical path | Mean | Spread | Imbalance ratio |
|---|---:|---:|---:|---:|
| `timing-based-1` | 30 s | 30 s | 0 s | 1.0 |
| `timing-based-2` | 20 s | 20 s | 0 s | 1.0 |

Both runs contain tied slowest branches because all measured branches
have equal durations.

The scenario medians are:

```text
critical path duration: 25 seconds
spread: 0 seconds
imbalance ratio: 1.0
```

## Expected comparison

Duration values are normalized to milliseconds in `analysis.json`.

| Metric | Baseline median | Candidate median | Absolute difference | Relative difference |
|---|---:|---:|---:|---:|
| `critical_path_duration` | 35000 ms | 25000 ms | -10000 ms | approximately -28.57% |
| `spread` | 20000 ms | 0 ms | -20000 ms | -100% |
| `imbalance_ratio` | approximately 1.4167 | 1.0 | approximately -0.4167 | approximately -29.41% |

Differences are calculated as:

```text
candidate - baseline
```

For these metrics, negative changes normally represent an improvement:

- a shorter critical branch reduces parallel-stage completion time;
- a smaller spread indicates more even branch durations;
- an imbalance ratio closer to `1.0` indicates better load balance.

## Branch count consistency

Both scenarios contain exactly two branches in every CI run.

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

A varying branch count is reported through different minimum and maximum
values and `consistent: false`.