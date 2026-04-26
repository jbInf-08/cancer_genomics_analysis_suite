# Benchmark Evidence

This project's performance claims should be validated with reproducible benchmark runs.

## Reproducible Harness

Use the CI harness in `.github/workflows/ci.yml` (`performance-test` job):

```bash
pytest CancerGenomicsSuite/tests/ -m performance --benchmark-only --benchmark-save=performance-baseline
```

## Artifact of Record

The canonical benchmark output is uploaded as the `performance-results` workflow artifact (from `.benchmarks/`).

## Local Re-run

```bash
pip install -e ".[dev,test]"
pytest CancerGenomicsSuite/tests/ -m performance --benchmark-only --benchmark-save=local-run
```

Compare local output with the latest CI artifact before updating README claims.
