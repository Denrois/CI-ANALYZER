# Thesis Baseline Reference

This directory contains a frozen snapshot of the CI experiment analyzer developed for the diploma thesis:

> Optimalizace CI/CD pipeline pomocí cache mechanismů a paralelizace testů

The snapshot is preserved as a behavioral reference for the new generalized **CI Experiment Analyzer** project.

Its purpose is to verify that the new implementation can reproduce the original thesis results while using a cleaner, configurable, and reusable architecture.

## Important

The files stored in the following directories represent the original thesis implementation, input data, and expected results:

- `original/`
- `supporting/`
- `input/`
- `expected/`

These files should not be modified during development of the new analyzer.

New production code will be implemented separately under `src/`.

## Directory structure

```text
reference/
├── README.md
├── original/
│   ├── analyze_ci_experiments.py
│   └── ci_select_tests.py
├── supporting/
│   └── test_file_timings.json
├── input/
│   ├── dependency_baseline/
│   ├── dependency_cache/
│   ├── docker_baseline/
│   ├── docker_cache_cold/
│   ├── docker_cache_first/
│   ├── docker_cache_fixed/
│   ├── sharding_baseline_original/
│   ├── sharding_timing_original/
│   ├── sharding_baseline_extended/
│   └── sharding_timing_extended/
└── expected/
    ├── computed_metrics.json
    ├── summary_tables.csv
    └── summary_report.md
```

## Original analyzer

The original thesis analyzer is located at:

```text
reference/original/analyze_ci_experiments.py
```

It is an offline Python CLI script that:

- loads experimental metrics from JSON and JSONL files;
- calculates descriptive statistics;
- compares baseline and optimized scenarios;
- normalizes duration values;
- separates local phase improvements from total scenario impact;
- calculates sharding critical-path and balance metrics;
- identifies the longest explicitly measured phase;
- generates JSON, CSV, and Markdown reports.

The original implementation is specific to the thesis experiments. Scenario names, metric names, and comparison pairs are defined directly in the script.

## Running the baseline

Run the analyzer from the repository root.

### PowerShell

```powershell
python reference/original/analyze_ci_experiments.py `
  --input reference/input `
  --output .tmp/thesis-baseline-output
```

The same command can be executed on one line:

```powershell
python reference/original/analyze_ci_experiments.py --input reference/input --output .tmp/thesis-baseline-output
```

The analyzer should generate:

```text
.tmp/thesis-baseline-output/
├── computed_metrics.json
├── summary_tables.csv
└── summary_report.md
```

The `.tmp/` directory is used only for locally generated verification output and should be excluded from Git.

## Verifying the output

The generated files should match the reference files stored in `reference/expected/`.

### Verify JSON

```powershell
python -c "import json; from pathlib import Path; expected=json.loads(Path('reference/expected/computed_metrics.json').read_text(encoding='utf-8-sig')); actual=json.loads(Path('.tmp/thesis-baseline-output/computed_metrics.json').read_text(encoding='utf-8-sig')); assert actual == expected, 'computed_metrics.json differs'; print('JSON OK')"
```

### Verify CSV

```powershell
python -c "from pathlib import Path; expected=Path('reference/expected/summary_tables.csv').read_text(encoding='utf-8-sig').splitlines(); actual=Path('.tmp/thesis-baseline-output/summary_tables.csv').read_text(encoding='utf-8-sig').splitlines(); assert actual == expected, 'summary_tables.csv differs'; print('CSV OK')"
```

### Verify Markdown

```powershell
python -c "from pathlib import Path; expected=Path('reference/expected/summary_report.md').read_text(encoding='utf-8-sig').splitlines(); actual=Path('.tmp/thesis-baseline-output/summary_report.md').read_text(encoding='utf-8-sig').splitlines(); assert actual == expected, 'summary_report.md differs'; print('Markdown OK')"
```

Expected verification output:

```text
JSON OK
CSV OK
Markdown OK
```

## Key expected results

### Dependency cache

Dependency preparation median:

- baseline: `2.652 s`
- optimized: `2.224 s`
- relative change: `-16.1%`

Total measured backend scenario:

- baseline: `56.020 s`
- optimized: `53.826 s`
- relative change: `-3.9%`

The dependency preparation phase improved noticeably, but it represented only a small part of the measured backend scenario. Its effect on the total duration was therefore limited.

### Docker build cache

Docker build median:

- baseline: `110.0 s`
- optimized: `47.5 s`
- relative change: `-56.8%`

Total measured Docker/Compose scenario:

- baseline: `137.0 s`
- optimized: `77.5 s`
- relative change: `-43.4%`

Docker build was the dominant measured phase in this scenario. Optimizing it therefore produced a significant improvement in the total measured duration.

### Original test-suite sharding

Critical-path median:

- baseline: `7.744 s`
- timing-based: `7.814 s`
- relative change: `+0.9%`

Imbalance ratio:

- baseline: `1.106`
- timing-based: `1.108`
- relative change: `+0.2%`

Timing-based sharding did not improve the original test suite. The original suite had too few independently distributable test files to benefit from timing-based balancing.

### Extended test-suite sharding

Critical-path median:

- baseline: `12.605 s`
- timing-based: `11.738 s`
- relative change: `-6.9%`

Imbalance ratio:

- baseline: `1.170`
- timing-based: `1.079`
- relative change: `-7.8%`

Shard-duration spread:

- baseline: `4.139 s`
- timing-based: `2.257 s`
- relative change: `-45.5%`

Timing-based sharding improved both the critical path and shard balance when the test suite provided enough independently distributable test files.

## Measurement limitations

The reported total duration represents explicitly measured experiment phases.

It does not represent the complete GitHub Actions workflow duration and excludes values such as:

- queue time;
- runner initialization before the measured interval;
- artifact upload after the measured interval;
- other unmeasured workflow overhead.

The original and extended sharding datasets represent different workloads and must be evaluated separately.

The experiments use repeated measurements and descriptive statistics. They do not claim formal statistical significance.

The detected bottleneck represents the longest explicitly measured phase according to its median duration. It does not represent the critical path of the complete GitHub Actions workflow graph.

For sharding experiments, the critical path represents the duration of the slowest shard in one parallel test run.

## Purpose in the new project

This snapshot will be used as:

- a behavioral reference;
- a regression-testing dataset;
- a thesis case study;
- evidence that the generalized analyzer reproduces the original results.

New functionality must not be implemented inside `reference/original/`.

Any intentional change to the reference data or expected output must be documented and reviewed separately.