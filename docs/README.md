# Cancer Genomics Analysis Suite — documentation index

This directory holds **curated, maintained** documentation for the suite. Titles link to files that **exist in this repository**; older plans referenced separate `user_guide/`, `api/`, or `deployment/` trees under `docs/` that are **not** present in the current project—use the links below instead.

## Getting started

| Document | Description |
|----------|-------------|
| [installation.md](installation.md) | Install from source, optional PyPI, Docker/Kubernetes notes, env vars |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | Dev setup, services, Helm, ArgoCD, operations |
| [LOCAL_HELM_QUICKSTART.md](LOCAL_HELM_QUICKSTART.md) | Minimal local cluster + Helm from repo root |
| [testing_confidence.md](testing_confidence.md) | What to test heavily; `critical` marker; coverage floor in `pyproject.toml` |
| [MD_GROMACS_AND_ENSEMBL.md](MD_GROMACS_AND_ENSEMBL.md) | GROMACS + Ensembl REST integration notes |

## Wider project docs (outside this folder)

| Location | Description |
|----------|-------------|
| [../README.md](../README.md) | Main project overview and quick start |
| [../PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md) | Accurate repo layout (Helm/Terraform under `CancerGenomicsSuite/`) |
| [../CancerGenomicsSuite/docs/bioinformatics_tools_integration.md](../CancerGenomicsSuite/docs/bioinformatics_tools_integration.md) | Bioinformatics tool integrations in the suite |
| [../CancerGenomicsSuite/api_docs/README.md](../CancerGenomicsSuite/api_docs/README.md) | OpenAPI / API documentation assets |
| [../CancerGenomicsSuite/DEPLOYMENT_GUIDE.md](../CancerGenomicsSuite/DEPLOYMENT_GUIDE.md) | Deeper deployment notes and Helm focus |
| [../data_collection/README.md](../data_collection/README.md) | Data collection scripts |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | How to contribute, tests, style |

## Community and license

- **Repository:** [github.com/jbInf-08/cancer_genomics_analysis_suite](https://github.com/jbInf-08/cancer_genomics_analysis_suite)
- **License:** [MIT License](../LICENSE) (see repository root)
- **Issues & discussions** use the GitHub project linked above; placeholder `your-org` URLs in legacy text should be ignored in favor of this URL.

**Last updated:** April 2026 (aligned with repository layout and `pyproject.toml` v1.0.0)
