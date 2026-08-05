# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-08-05

### Added

- installable Python package using a `src` layout;
- `ci-analyzer` command-line interface;
- separate `validate` and `analyze` commands;
- YAML-based experiment configuration;
- CSV, JSON, and JSONL scenario readers;
- configurable input field mapping;
- configuration and input data validation;
- duration normalization to milliseconds;
- descriptive scenario statistics:
  count, median, mean, minimum, maximum, and sample standard deviation;
- baseline-versus-candidate median comparisons;
- absolute and relative difference calculations;
- safe handling of single-observation scenarios;
- safe handling of zero baseline medians;
- configurable local-versus-total impact analysis;
- detection of substantial local improvements with limited end-to-end
  impact;
- bottleneck candidate detection for measured pipeline phases;
- deterministic handling of tied bottleneck candidates;
- parallel-stage analysis based on repeated CI runs;
- parallel critical-path duration, spread, and imbalance-ratio metrics;
- slowest-branch and tied-branch reporting;
- branch-count consistency detection;
- JSON reports in `analysis.json`;
- flat comparison summaries in `summary.csv`;
- human-readable reports in `report.md`;
- minimal and parallel-stage end-to-end examples;
- unit, integration, and CLI test coverage;
- GitHub Actions quality checks;
- Ruff formatting and formatting enforcement;
- mypy strict type checking.

### Known limitations

- comparisons currently use scenario medians;
- bottleneck candidates are based only on configured measured phase
  durations;
- parallel critical-path duration covers one configured parallel stage
  rather than the dependency graph of the complete CI pipeline;
- automatic timing-based shard planning is not yet implemented;
- impact thresholds apply to relative median changes.