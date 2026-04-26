# Cancer Genomics Analysis Suite

[![CI](https://github.com/jbInf-08/cancer_genomics_analysis_suite/actions/workflows/ci.yml/badge.svg)](https://github.com/jbInf-08/cancer_genomics_analysis_suite/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## Golden path

```bash
pip install -e .
pytest CancerGenomicsSuite/tests/unit -v
cancer-genomics
```

Benchmark evidence and reproducibility details: [docs/BENCHMARKS.md](docs/BENCHMARKS.md).

A comprehensive, production-ready platform for cancer genomics analysis featuring real-time mutation detection, clinical data integration, machine learning-based outcome prediction, and multi-omics data analysis.

## Features

### Core Capabilities
- **Real-time Mutation Detection**: Live streaming mutation analysis with instant alerts
- **Clinical Data Integration**: Seamless integration with EHR systems (Epic, Cerner, Allscripts)
- **Machine Learning Pipeline**: Advanced ML models for outcome prediction and risk assessment
- **Multi-omics Analysis**: Integrated analysis of genomics, transcriptomics, and proteomics data
- **Graph Database Analytics**: Neo4j-powered knowledge graph for complex relationship analysis

### Bioinformatics Tools Integration
- **Galaxy Integration**: Access Galaxy workflows, tools, and data analysis capabilities
- **R Integration**: Comprehensive statistical analysis with R packages (DESeq2, limma, ggplot2)
- **MATLAB Integration**: Numerical computing, signal processing, and optimization
- **PyMOL Integration**: Molecular visualization and structure analysis
- **Text Editors**: Support for nano, vim, emacs, notepad++, and other editors
- **A Plasmid Editor (APE)**: Plasmid design, analysis, and visualization
- **IGV Integration**: Genomic data visualization and analysis
- **GROMACS Integration**: Molecular dynamics simulations
- **WGSIM Tools**: Read simulation and variant calling (wgsim, dwgsim)
- **Neurosnap Integration**: Neuroscience data analysis
- **Tamarind Bio**: Bioinformatics workflow execution

### Technical Features
- **Stream Processing**: Apache Kafka for real-time data processing
- **Pipeline Orchestration**: Snakemake and Nextflow for scalable workflow management
- **Perl Support**: Execute Perl-based scripts as pipelines via the workflow executor
- **Container Orchestration**: Kubernetes-native deployment with Helm charts
- **Infrastructure as Code**: Terraform for AWS/GCP infrastructure provisioning
- **GitOps Deployment**: ArgoCD for automated, declarative deployments
- **Comprehensive Monitoring**: Prometheus, Grafana, and custom alerting rules
- **Security**: TLS encryption, RBAC, network policies, and secrets management
- **Bioinformatics Tools**: Integrated access to 11+ popular bioinformatics tools
- **CLI Support**: Command-line interfaces for all integrated tools
- **Plugin System**: Modular architecture for easy extension

## Prerequisites

### System Requirements
- **Python**: 3.8+
- **Kubernetes**: 1.28+
- **Helm**: 3.12+
- **kubectl**: Latest
- **Terraform**: 1.6+
- **Docker**: Latest
- **Git**: Latest

### Cloud Provider Setup
- **AWS**: EKS cluster, RDS, ElastiCache, S3, Secrets Manager
- **GCP**: GKE cluster, Cloud SQL, Memorystore, Cloud Storage, Secret Manager

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/jbInf-08/cancer_genomics_analysis_suite.git
cd cancer_genomics_analysis_suite
```

### 2. Install Dependencies
```bash
# Install the package
pip install -e .

# Or install from requirements
pip install -r CancerGenomicsSuite/requirements.txt
```

### 3. Deploy Infrastructure
Terraform for AWS and GCP lives under the application tree:

```bash
# AWS
cd CancerGenomicsSuite/terraform/aws
terraform init
terraform plan
terraform apply

# GCP
cd CancerGenomicsSuite/terraform/gcp
terraform init
terraform plan
terraform apply
```

### 4. Deploy Application
```bash
# Using ArgoCD (GitOps; manifests are under the application tree)
kubectl apply -f CancerGenomicsSuite/argocd/argocd-project.yaml
kubectl apply -f CancerGenomicsSuite/argocd/argocd-app.yaml

# Using Helm (from repository root; alternative to ArgoCD)
helm install cancer-genomics ./CancerGenomicsSuite/helm/cancer-genomics-analysis-suite \
  --namespace cancer-genomics \
  --create-namespace \
  --values ./CancerGenomicsSuite/helm/cancer-genomics-analysis-suite/values-production.yaml
```

### 5. Local development (Dash dashboard)
After `pip install -e .` and copying `.env.example` to `.env` (or using `CancerGenomicsSuite/environment.template`), start the main dashboard (default port from `PORT` / config, often **8050**):

```bash
cancer-genomics
```

**REST app factory (optional):** `python CancerGenomicsSuite/run_flask_app.py` (uses `CancerGenomicsSuite.app.create_app`).

### 6. Access the Application
- **Web Interface**: https://cancer-genomics.yourdomain.com
- **API**: https://api.cancer-genomics.yourdomain.com
- **Grafana**: https://grafana.cancer-genomics.yourdomain.com
- **Prometheus**: https://prometheus.cancer-genomics.yourdomain.com

### 7. Using Bioinformatics Tools
```bash
# List all available bioinformatics tools
cancer-genomics-cli

# Use specific tools
cancer-genomics-cli galaxy --list-workflows
cancer-genomics-cli r --install-package DESeq2
cancer-genomics-cli pymol --fetch 1CRN
```

### Running Perl Pipelines

Perl scripts (`.pl`) are detected and executed via the built-in Perl manager. Register a pipeline pointing to your `.pl` and pass args/env in `config`:

```python
from CancerGenomicsSuite.modules.pipeline_orchestration.workflow_executor import WorkflowExecutor

executor = WorkflowExecutor()
executor.registry.register_pipeline(
    name="perl_example",
    pipeline_type="annotation",
    description="Example Perl script pipeline",
    script_path="/path/to/script.pl",
)

workflow_id = executor.execute_workflow(
    pipeline_name="perl_example",
    config={
        "perl_args": ["--input", "data.vcf"],
        "perl_env": {"PERL5LIB": "/app/perl5"},
    },
)
```

### Seurat, HDOCK, HADDOCK, SATurn, SeqAnt

- **Seurat (R)**: Register an `.R` script; executor detects `Seurat` usage or `.R` extension. Pass args via `r_args`, env via `r_env`.
- **HDOCK**: Register a pipeline with a placeholder script path and provide `receptor`, `ligand`, optional `hdock_args` in `config`.
- **HADDOCK**: Provide `project_dir`, optional `haddock_config`, and `haddock_args` in `config`.
- **SATurn**: Provide a `workflow_file` (script path) and `saturn_args` in `config`.
- **SeqAnt**: Register the SeqAnt script; executor infers interpreter from extension/shebang. Pass `seqant_args` and `seqant_env`.

## Project Structure

```
cancer_genomics_analysis_suite/
├── CancerGenomicsSuite/         # Installed package: Dash app, modules, k8s, Helm, Terraform, tests
│   ├── app/                    # Flask app factory (REST/auth/dashboard)
│   ├── main_dashboard.py        # `cancer-genomics` — Dash + plugin modules
│   ├── modules/                # Analysis & tool integrations
│   ├── k8s/                    # Optional raw K8s manifests; Helm is primary for deploy
│   ├── helm/cancer-genomics-analysis-suite/
│   ├── argocd/
│   ├── terraform/              # aws/ and gcp/
│   ├── tests/                  # Pytest; options in root pyproject.toml
│   ├── requirements.txt
│   ├── api_docs/               # OpenAPI / API notes
│   └── ...                     # see PROJECT_STRUCTURE.md
├── data_collection/            # ETL-style collectors
├── docker/                    # e.g. docker-compose.db.yml
├── docs/                      # Installation, deployment, testing, helm quickstart
├── scripts/                   # setup_postgresql.py, etc.
├── workflows/                 # e.g. sample_analysis_workflow.py
├── .github/workflows/         # ci.yml, cd.yml, security.yml
├── pyproject.toml, .env.example, README.md
```

Long-form layout and file naming: [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md).

## Configuration

### Mutation module boundaries

- `mutation_analysis`: core mutation-centric analytics and descriptive/statistical workflows.
- `mutation_effect_predictor`: impact/effect estimation logic (functional effect scoring and model-assisted interpretation).
- `mutation_predictor`: predictive tasks that classify/forecast mutation-related outcomes.

When adding new mutation functionality, place code by concern above and avoid creating additional sibling modules with overlapping responsibilities.

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# Redis
REDIS_URL=redis://host:6379/0

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# External APIs
ENSEMBL_API_KEY=your-key
UNIPROT_API_KEY=your-key
CLINVAR_API_KEY=your-key
```

## Testing

### Test Suites
```bash
# Entire suite (default pytest config includes coverage; gate is 10% total line coverage)
pytest CancerGenomicsSuite/tests/ -v

# Unit tests
pytest CancerGenomicsSuite/tests/unit/ -v

# Integration tests
pytest CancerGenomicsSuite/tests/integration/ -v

# End-to-end tests
pytest CancerGenomicsSuite/tests/e2e/ -v

# Performance smoke tests
pytest CancerGenomicsSuite/tests/performance/ -v

# Security-related pytest markers (static analysis is separate, below)
pytest CancerGenomicsSuite/tests/security/ -v

# Static security scans (not pytest)
bandit -r CancerGenomicsSuite/
safety check
```

R integration tests (`tests/unit/test_r_integration.py`) are **skipped on Windows** at import time so `rpy2` does not load during collection; run them on **Linux or WSL** with R and optional `pip install -e ".[r-integration]"`.

During `pytest`, a session autouse fixture sets **`CGAS_TEST_UPLOAD_FOLDER`** to a single directory from **`tmp_path_factory`**, and **`TestConfig`** uses it for **`UPLOAD_FOLDER`** so repeated `TestConfig()` calls do not create new temp trees for every instance.

**Strategy:** prioritize confidence in high-risk areas; the global coverage number is a regression ratchet, not a target to maximize. See [docs/testing_confidence.md](docs/testing_confidence.md). Run a small **high-confidence** subset with:

```bash
pytest CancerGenomicsSuite/tests/ -m critical -v --no-cov
```

## Deployment

### Environments
- **Development**: Single-node cluster for development
- **Staging**: Multi-node cluster for testing
- **Production**: High-availability cluster with monitoring

### Deployment Strategies
- **Blue-Green**: Zero-downtime deployments
- **Rolling Updates**: Gradual rollout with health checks
- **Canary**: Risk-free production deployments

## 📊 Performance

### Benchmarks
- **Mutation Processing**: 10,000+ mutations/second
- **Clinical Data Ingestion**: 1M+ records/hour
- **ML Pipeline**: 100+ samples/hour
- **API Response Time**: <100ms (95th percentile)

## Contributing

### Development Setup
```bash
# Clone repository
git clone https://github.com/jbInf-08/cancer_genomics_analysis_suite.git
cd cancer_genomics_analysis_suite

# Install dependencies
pip install -e .[dev]

# Set up pre-commit hooks
pre-commit install

# Run tests
pytest CancerGenomicsSuite/tests/ -v
```

### Contribution Guidelines
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## Documentation

### Additional Resources
- [Project structure (detailed)](PROJECT_STRUCTURE.md)
- [Installation](docs/installation.md)
- [docs index](docs/README.md) — lists **existing** top-level guides under `docs/`
- [Deployment (overview)](docs/DEPLOYMENT_GUIDE.md) and [Helm in-cluster details](CancerGenomicsSuite/DEPLOYMENT_GUIDE.md)
- [Local Kubernetes / Helm quickstart](docs/LOCAL_HELM_QUICKSTART.md)
- [API / OpenAPI notes](CancerGenomicsSuite/api_docs/README.md)
- [Bioinformatics tools (suite)](CancerGenomicsSuite/docs/bioinformatics_tools_integration.md)
- [Testing strategy](docs/testing_confidence.md)
- [GROMACS / Ensembl (MD + REST)](docs/MD_GROMACS_AND_ENSEMBL.md)
- [Data collection](data_collection/README.md)
- [Contributing](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md)

## Support

### Getting Help
- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and community support
- **Documentation**: Comprehensive guides and references
- **Email Support**: jbautista0055@gmail.com

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Contributors**: All the amazing developers who contributed to this project
- **Open Source**: Built on top of excellent open-source tools and libraries
- **Community**: The cancer genomics research community for feedback and support
- **Institutions**: Research institutions and hospitals using this platform

---


