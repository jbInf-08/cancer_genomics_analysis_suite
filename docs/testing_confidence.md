# Testing for confidence (not coverage for its own sake)

This project uses **automated tests** and a **modest global coverage floor** so changes do not silently break the app. The goal is **high confidence where it matters**, not a high percentage on every file.

## Principles

1. **Test behavior that carries risk** — wrong results, security boundaries, data loss, broken deployments, or confusing failures in production-like paths.
2. **Prefer small, fast tests** with clear assertions; use **mocks at system boundaries** (HTTP, subprocess, filesystem) rather than mocking everything.
3. **Raise the global coverage floor slowly** only when the measured total actually increases (see `pyproject.toml` `--cov-fail-under`). It is a **ratchet**, not a score to maximize.
4. **Do not chase 100%** repository-wide. Large UI, optional integrations, and glue code rarely justify full line coverage.

## Where confidence matters most (prioritize here)

Use judgment; typical **high-value** areas for this suite include:

| Area | Why it matters |
|------|----------------|
| **App factory & core HTTP** (`create_app`, `/health`, key APIs) | Deployment and monitoring depend on them. |
| **Test / runtime configuration** (`TestConfig`, secrets, upload paths) | Misconfiguration breaks all environments. |
| **Mutation analysis pipeline** (parsing, classification, summaries) | Core science/clinical interpretation path. |
| **Reporting** (HTML/PDF generation, templates) | User-visible deliverables; regressions are obvious to customers. |
| **Workflow orchestration** (executors, job lifecycle) | Silent job failures or partial runs are costly. |
| **External API clients** (with mocks) | Contracts and failure modes (timeouts, bad payloads). |

Low **priority** for blanket coverage: Dash layout-only modules, optional tool integrations without stable CI binaries, and one-off scripts—test these when you change them or when bugs appear.

## The `critical` marker

Selected tests are marked **`@pytest.mark.critical`**. These should be **minimal**, **stable**, and **representative** of product risk—not every test in a file.

Run only critical tests (fast smoke before release or after risky refactors):

```bash
pytest CancerGenomicsSuite/tests/ -m critical -v --no-cov
```

Add **`critical`** only when:

- The test guards a **regression** you care about, or
- It validates **invariants** for a high-risk subsystem (see table above).

Avoid marking entire modules with `pytestmark = pytest.mark.critical` unless the whole file is genuinely core.

## Coverage reports

After `pytest`:

- **Terminal**: summary and missing lines for touched files.
- **HTML**: `htmlcov/index.html` — use it to **find gaps next to code you are changing**, not to “paint” unrelated files green.

## Checklist before merging risky changes

- [ ] Tests updated or added for the **behavior** you changed (not only to satisfy coverage).
- [ ] If touching security or config: run **`pytest …/security/`** and relevant **`critical`** tests.
- [ ] If touching reporting or pipelines: run the **reporting** and **workflow** tests you touched.
- [ ] Global suite still passes: **`pytest CancerGenomicsSuite/tests/`** (includes coverage gate from `pyproject.toml`).

This document should evolve with the product: **adjust the priority table** as modules gain or lose importance.
