# Benchmark harness (no baseline numbers yet)

**No baseline numbers are recorded in this file.** The suite includes lightweight timing smoke tests and CI wiring for future systematic benchmarking; treat any performance claims as TBD until a recorded run is checked in or published elsewhere.

## Reproducible harness (CI on `main`)

The workflow job `performance-test` in `.github/workflows/ci.yml` runs:

```bash
pytest CancerGenomicsSuite/tests/ -m performance --benchmark-only --benchmark-save=performance-baseline
```

If/when `pytest-benchmark` is used in tests, the canonical output is intended to be uploaded as the `performance-results` artifact (from `.benchmarks/`).

## Local re-run (same flags as CI)

```bash
pip install -e ".[dev,test]"
pytest CancerGenomicsSuite/tests/ -m performance --benchmark-only --benchmark-save=local-run
```

Compare local output with the latest CI artifact before updating the main README with numeric claims.
