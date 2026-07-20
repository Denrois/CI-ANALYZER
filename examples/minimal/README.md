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