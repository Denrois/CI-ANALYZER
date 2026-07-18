# Minimal CSV Example

This example demonstrates the smallest supported CI experiment analysis.

It compares two scenarios:

- `baseline`
- `optimized`

The input data is stored in CSV files. Column names are mapped to analyzer metrics through `experiment.yaml`.

## Run

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

## Expected medians

| Metric | Baseline | Optimized | Absolute difference | Relative difference |
|---|---:|---:|---:|---:|
| `install_duration` | 12.0 | 9.0 | -3.0 | -25.0% |
| `total_duration` | 54.0 | 48.0 | -6.0 | -11.11% |

A negative difference means that the candidate value is lower than the baseline value.
For duration metrics, this normally represents an improvement.