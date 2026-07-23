# Minimal CSV Example

This example demonstrates the smallest supported CI experiment analysis.

It compares two scenarios:

- `baseline`
- `optimized`

The input data is stored in CSV files. Column names are mapped to analyzer metrics through `experiment.yaml`.

## Validate

Validate both the experiment configuration and the referenced CSV data:

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

## Analyze

Execute from the repository root:

```powershell
ci-analyzer analyze `
  --config examples/minimal/experiment.yaml `
  --output .tmp/minimal-report
```

The same command on one line:

```powershell
ci-analyzer analyze --config examples/minimal/experiment.yaml --output .tmp/minimal-report
```

The analyzer creates:

```text
.tmp/minimal-report/
└── analysis.json
```

## Duration normalization

Duration metrics are normalized to milliseconds in `analysis.json`, regardless of the source unit configured in YAML.

The supported duration units are:

- `milliseconds`
- `seconds`
- `minutes`

The CSV files in this example contain values in seconds, while the resulting JSON report contains the corresponding values in milliseconds.

## Expected medians

| Metric | Baseline | Optimized | Absolute difference | Relative difference |
|---|---:|---:|---:|---:|
| `install_duration` | 12000 ms | 9000 ms | -3000 ms | -25.0% |
| `total_duration` | 54000 ms | 48000 ms | -6000 ms | -11.11% |

The difference is calculated as:

```text
candidate - baseline
```

A negative difference means that the candidate value is lower than the baseline value.

For duration metrics, a negative difference normally represents an improvement.

## Generated analysis

The example produces:

```text
<output-directory>/analysis.json
```

The report includes descriptive statistics for both `baseline` and
`optimized` scenarios:

- number of observations;
- median;
- arithmetic mean;
- minimum and maximum;
- sample standard deviation.

It also compares the configured scenario medians and reports absolute and
relative changes.

All duration values are represented in milliseconds in the generated
report, even though the source CSV values are expressed in seconds.

## Local-versus-total impact

The example uses the following impact thresholds:

```yaml
analysis:
  local_improvement_threshold_pct: 10.0
  total_impact_threshold_pct: 5.0
```

The `install_duration` metric has the `phase` role and improves from a
median of `12000.0` milliseconds to `9000.0` milliseconds:

```text
relative improvement: 25.0%
```

The `total_duration` metric has the `total` role and improves from a
median of `54000.0` milliseconds to `48000.0` milliseconds:

```text
relative improvement: approximately 11.11%
```

The local improvement exceeds the configured `10.0%` threshold, while
the total improvement also exceeds the configured `5.0%` threshold.

The expected classification is therefore:

```json
{
  "substantial_local_improvement": true,
  "limited_total_improvement": false,
  "limited_end_to_end_impact": false,
  "warning": null
}
```

This example demonstrates that the local optimization produces a
meaningful end-to-end pipeline improvement.