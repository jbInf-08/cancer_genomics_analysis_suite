# Project structure

This file reflects the **current** layout of the [cancer_genomics_analysis_suite](https://github.com/jbInf-08/cancer_genomics_analysis_suite) repository. The Python application and deployment assets live under **`CancerGenomicsSuite/`**; the repo root holds packaging, `docs/`, and supporting tooling.

## Repository root

| Path | Purpose |
|------|---------|
| `CancerGenomicsSuite/` | Installable package (`cancer-genomics-analysis-suite` in `pyproject.toml`) |
| `data_collection/` | Standalone collector scripts and orchestration ([data_collection/README.md](data_collection/README.md)) |
| `docker/` | Compose files for local stacks (e.g. `docker-compose.db.yml` for DB services) |
| `docs/` | Curated guides: [installation](docs/installation.md), [deployment](docs/DEPLOYMENT_GUIDE.md), [testing](docs/testing_confidence.md), [Helm local run](docs/LOCAL_HELM_QUICKSTART.md), [MD/GROMACS/Ensembl](docs/MD_GROMACS_AND_ENSEMBL.md) |
| `scripts/` | Utility scripts (e.g. [scripts/setup_postgresql.py](scripts/setup_postgresql.py)) |
| `workflows/` | Example workflows (e.g. [workflows/sample_analysis_workflow.py](workflows/sample_analysis_workflow.py)) |
| `pyproject.toml` | Package metadata, console scripts, pytest/coverage, optional extras |
| `.env.example` | Environment template; copy to `.` as `.env` for local work |
| `.github/workflows/` | `ci.yml`, `cd.yml`, `security.yml`, `ci-cd-pipeline.yml` |
| `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md`, `README.md` | Project governance and overview |

**Not** at repo root (historical docs sometimes assumed otherwise): there is no top-level `helm/`, `terraform/`, or `argocd/`; those are under `CancerGenomicsSuite/`. There is no top-level `tests/` tree; tests are in **`CancerGenomicsSuite/tests/`** (driven by `[tool.pytest]` in `pyproject.toml`).

**Optional / legacy requirement files:** dependency management is **primarily** via `pyproject.toml`. A snapshot exists at [CancerGenomicsSuite/requirements.txt](CancerGenomicsSuite/requirements.txt) for reference or constrained installs.

## `CancerGenomicsSuite/` (main package)

| Area | Role |
|------|------|
| `main_dashboard.py` | Dash UI; console entry: `cancer-genomics` |
| `app/` | Flask `create_app`, auth, SQLAlchemy, dashboard routes |
| `config/` | Settings and environment-based configuration |
| `modules/` | Feature and integration modules (genomics, ML, pipelines, external tools, etc.) |
| `plugin_registry.py` | Loads module plugins for the Dash UI |
| `api_integrations/` | Sync/clients (e.g. ClinVar) |
| `workflows/`, `tasks/`, `celery_worker.py` / `run_celery_worker.py` | Pipelines and background work |
| `cli_bioinformatics_tools.py` | Console: `cancer-genomics-cli` |
| `run_flask_app.py` | Run Flask app from factory (dev/REST) |
| `k8s/` | Raw Kubernetes (monitoring, kustomize) — use together with or beside Helm |
| `helm/cancer-genomics-analysis-suite/` | **Primary** Kubernetes packaging |
| `terraform/aws`, `terraform/gcp` | Infrastructure as code (also `terraform/main.tf` for shared layout) |
| `argocd/` | Argo CD Application/Project and related apps |
| `scripts/`, `docker-compose*.yml` | App-local scripts and compose variants |
| `api_docs/` | OpenAPI and API documentation assets |
| `docs/` | In-package docs, e.g. [bioinformatics_tools_integration.md](CancerGenomicsSuite/docs/bioinformatics_tools_integration.md) and `index.md` |
| `docs/` in package | [DEPLOYMENT_GUIDE.md](CancerGenomicsSuite/DEPLOYMENT_GUIDE.md) and related summaries in-tree |
| `tests/` | `unit/`, `integration/`, `e2e/`, `performance/`, `security/`, `fixtures/`, `mocks/` |
| `static/`, `templates/` | Web assets for app shell |
| `examples/` | Snippets and example scripts (not the same as `workflows/` at repo root) |

## Console scripts (`pyproject.toml`)

- `cancer-genomics` → `CancerGenomicsSuite.main_dashboard:main`
- `cancer-genomics-cli` → `CancerGenomicsSuite.cli_bioinformatics_tools:main`

## Tests

- Run: `pytest CancerGenomicsSuite/tests/ -v` (or from repo root; `testpaths` is set in `pyproject.toml`).
- Coverage fail-under, markers (`critical`, etc.): see [docs/testing_confidence.md](docs/testing_confidence.md).

## Related documentation

- [README.md](README.md) — feature overview, quick start, and links
- [docs/README.md](docs/README.md) — index of `docs/*.md` files that exist in this tree

---

This structure is updated to match the repository as maintained in source control. If you add top-level `helm/`, a root `tests/`, or publish a PyPI release, update this file and the root README in the same change.
