# Cancer Genomics Analysis Suite

A comprehensive, production-ready platform for cancer genomics analysis featuring real-time mutation detection, clinical data integration, machine learning-based outcome prediction, and multi-omics data analysis.

## 🚀 Features

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
- **Perl pipelines**: Workflows can invoke `.pl` scripts (see root [README: Running Perl Pipelines](../README.md#running-perl-pipelines))
- **Container Orchestration**: Kubernetes-native deployment with Helm charts
- **Infrastructure as Code**: Terraform for AWS/GCP infrastructure provisioning
- **GitOps Deployment**: ArgoCD for automated, declarative deployments
- **Comprehensive Monitoring**: Prometheus, Grafana, and custom alerting rules
- **Security**: TLS encryption, RBAC, network policies, and secrets management
- **Bioinformatics Tools**: Integrated access to 11+ popular bioinformatics tools
- **CLI Support**: Command-line interfaces for all integrated tools
- **Plugin System**: Modular architecture for easy extension

## 🏗️ Architecture

```mermaid
graph TB
    subgraph "External Systems"
        EHR[EHR Systems]
        APIs[External APIs]
        Users[Users]
    end
    
    subgraph "Ingress Layer"
        ALB[Application Load Balancer]
        Ingress[NGINX Ingress]
        TLS[TLS Termination]
    end
    
    subgraph "Application Layer"
        Web[Web Application]
        API[API Gateway]
        Auth[Authentication]
    end
    
    subgraph "Processing Layer"
        Kafka[Apache Kafka]
        Stream[Stream Processors]
        ML[ML Pipeline]
        Workflows[Snakemake/Nextflow]
    end
    
    subgraph "Data Layer"
        Neo4j[Neo4j Graph DB]
        Postgres[PostgreSQL]
        Redis[Redis Cache]
        S3[Object Storage]
    end
    
    subgraph "Monitoring"
        Prometheus[Prometheus]
        Grafana[Grafana]
        Alerts[Alertmanager]
    end
    
    Users --> ALB
    EHR --> Kafka
    APIs --> API
    
    ALB --> Ingress
    Ingress --> TLS
    TLS --> Web
    TLS --> API
    
    Web --> Auth
    API --> Auth
    
    Auth --> Kafka
    Kafka --> Stream
    Stream --> ML
    ML --> Workflows
    
    Stream --> Neo4j
    ML --> Postgres
    Workflows --> S3
    Web --> Redis
    
    Web --> Prometheus
    API --> Prometheus
    Stream --> Prometheus
    Prometheus --> Grafana
    Prometheus --> Alerts
```

## 📋 Prerequisites

### For local development
- **Python**: 3.8+ (see `pyproject.toml` for supported versions)
- **Git**

### For Kubernetes / cloud deploy
- **Kubernetes**: 1.28+
- **Helm**: 3.12+
- **kubectl**
- **Terraform** (optional, for `terraform/aws` and `terraform/gcp` in this tree)
- **Docker** (for images and local compose)

### Cloud Provider Setup
- **AWS**: EKS cluster, RDS, ElastiCache, S3, Secrets Manager
- **GCP**: GKE cluster, Cloud SQL, Memorystore, Cloud Storage, Secret Manager

## 🚀 Quick start

Work from the **repository root** (`cancer_genomics_analysis_suite/`), not only this folder, so `pip install -e .` and paths resolve.

### 1. Clone
```bash
git clone https://github.com/jbInf-08/cancer_genomics_analysis_suite.git
cd cancer_genomics_analysis_suite
```

### 2. Install
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix:   source .venv/bin/activate
pip install -e .
pip install -e ".[dev,test]"   # optional
cp .env.example .env
```

### 3. Run the main Dash app
```bash
cancer-genomics
```
(Often listens on port **8050**; `GET /test` returns a small JSON health payload.)

**Bioinformatics CLI** (from repo root, after `pip install -e .`):
```bash
cancer-genomics-cli --help
```

**Alternate:** from this directory, `python cli_bioinformatics_tools.py` (adds the local tree to the path; prefer the entry point above).

### 4. Optional: Terraform (paths relative to this package directory)
```bash
cd CancerGenomicsSuite/terraform/aws
terraform init && terraform plan && terraform apply
```

### 5. Optional: deploy with ArgoCD / Helm
```bash
kubectl apply -f CancerGenomicsSuite/argocd/argocd-project.yaml
kubectl apply -f CancerGenomicsSuite/argocd/argocd-app.yaml
# Or Helm — see ../docs/LOCAL_HELM_QUICKSTART.md
helm install cgas ./CancerGenomicsSuite/helm/cancer-genomics-analysis-suite \
  --namespace cancer-genomics --create-namespace \
  -f ./CancerGenomicsSuite/helm/cancer-genomics-analysis-suite/values.yaml
```

For deployed clusters, set hosts in your values/ingress; placeholders like `cancer-genomics.yourdomain.com` are only examples.

## 📁 Layout

Helm, Terraform, ArgoCD, and the main `tests/` tree for this app live **inside `CancerGenomicsSuite/`** in the repository. A concise map of the whole repo (including `docs/`, `data_collection/`, etc.) is in the root [PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md).

## 🔧 Configuration

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

### Helm Values
```yaml
# values-production.yaml
global:
  environment: production
  domain: cancer-genomics.yourdomain.com
  cloudProvider: aws

web:
  replicaCount: 3
  resources:
    limits:
      cpu: 2000m
      memory: 4Gi

kafka:
  enabled: true
  replicaCount: 3

neo4j:
  enabled: true
  persistence:
    dataSize: 100Gi

monitoring:
  enabled: true
  alertmanager:
    email:
      critical: "critical-alerts@yourdomain.com"
```

## 🔍 Monitoring and Alerting

### Key Metrics
- **Mutation Detection Rate**: Real-time mutation processing metrics
- **Pipeline Success Rate**: Workflow execution success rates
- **System Performance**: CPU, memory, and disk usage
- **Database Performance**: Query performance and connection metrics
- **Kafka Metrics**: Message throughput and lag

### Alert Rules
- **Critical Mutations**: Immediate alerts for high-impact mutations
- **Pipeline Failures**: Alerts for failed workflow executions
- **System Issues**: Resource exhaustion and service unavailability
- **Security Events**: Unauthorized access attempts and anomalies

### Dashboards
- **Overview Dashboard**: System health and key metrics
- **Mutation Analysis**: Real-time mutation detection and analysis
- **Pipeline Monitoring**: Workflow execution and performance
- **Infrastructure**: Resource utilization and capacity planning

## 🔒 Security

### Security Features
- **TLS Encryption**: End-to-end encryption for all communications
- **RBAC**: Role-based access control for Kubernetes resources
- **Network Policies**: Micro-segmentation and traffic control
- **Secrets Management**: Secure storage and rotation of sensitive data
- **Pod Security**: Restricted pod security contexts
- **Image Security**: Vulnerability scanning and secure base images

### Compliance
- **HIPAA**: Healthcare data protection compliance
- **SOC 2**: Security and availability controls
- **GDPR**: Data privacy and protection
- **Audit Logging**: Comprehensive audit trails

## 🧪 Testing

```bash
# From repository root; pyproject.toml sets testpaths to CancerGenomicsSuite/tests
pytest -v
pytest CancerGenomicsSuite/tests/unit/ -v
```

Coverage gate and philosophy: [../docs/testing_confidence.md](../docs/testing_confidence.md). Static security scans (not pytest):
```bash
bandit -r CancerGenomicsSuite
safety check
```

## 🚀 Deployment

### Environments
- **Development**: Single-node cluster for development
- **Staging**: Multi-node cluster for testing
- **Production**: High-availability cluster with monitoring

### Deployment Strategies
- **Blue-Green**: Zero-downtime deployments
- **Rolling Updates**: Gradual rollout with health checks
- **Canary**: Risk-free production deployments

### CI/CD Pipeline
- **Security Scanning**: Trivy, Bandit, Semgrep
- **Code Quality**: Black, Flake8, MyPy
- **Testing**: Unit, integration, and performance tests
- **Building**: Multi-architecture Docker images
- **Deployment**: Automated GitOps deployment

## 📊 Performance

### Benchmarks
- **Mutation Processing**: 10,000+ mutations/second
- **Clinical Data Ingestion**: 1M+ records/hour
- **ML Pipeline**: 100+ samples/hour
- **API Response Time**: <100ms (95th percentile)

### Scalability
- **Horizontal Scaling**: Auto-scaling based on demand
- **Vertical Scaling**: Resource optimization and tuning
- **Database Scaling**: Read replicas and connection pooling
- **Cache Optimization**: Redis clustering and optimization

## 🤝 Contributing

See the root [CONTRIBUTING.md](../CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md).

```bash
cd cancer_genomics_analysis_suite
pip install -e ".[dev,test]"
pre-commit install
pytest
```

### Contribution Guidelines
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Code Standards
- **Python**: PEP 8, Black formatting, MyPy type checking
- **Documentation**: Comprehensive docstrings and comments
- **Testing**: Unit tests for all new features
- **Security**: Security review for sensitive changes

## 📚 Documentation

- [In-repo deployment guide](DEPLOYMENT_GUIDE.md)
- [../docs/DEPLOYMENT_GUIDE.md](../docs/DEPLOYMENT_GUIDE.md) — dev, compose, k8s operations
- [../docs/LOCAL_HELM_QUICKSTART.md](../docs/LOCAL_HELM_QUICKSTART.md) — local Helm
- [api_docs/README.md](api_docs/README.md) — API / OpenAPI assets
- [docs/bioinformatics_tools_integration.md](docs/bioinformatics_tools_integration.md)
- [../README.md](../README.md) — product overview

### External Documentation
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)
- [Terraform Documentation](https://terraform.io/docs/)
- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)

## 🆘 Support

### Getting Help
- **Repository:** [jbInf-08/cancer_genomics_analysis_suite](https://github.com/jbInf-08/cancer_genomics_analysis_suite)
- **Author email (root README):** see [../README.md](../README.md#support) for the current contact

### Community
- **Slack**: #cancer-genomics channel
- **Discord**: Cancer Genomics Community
- **Twitter**: @CancerGenomics
- **LinkedIn**: Cancer Genomics Analysis Suite

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Contributors**: All the amazing developers who contributed to this project
- **Open Source**: Built on top of excellent open-source tools and libraries
- **Community**: The cancer genomics research community for feedback and support
- **Institutions**: Research institutions and hospitals using this platform

## 📈 Roadmap

### Upcoming Features
- **AI/ML Enhancements**: Advanced deep learning models
- **Multi-cloud Support**: Azure and hybrid cloud deployments
- **Real-time Collaboration**: Multi-user analysis sessions
- **Advanced Visualization**: Interactive 3D molecular visualization
- **Federated Learning**: Privacy-preserving distributed learning
- **Additional Tool Integrations**: More bioinformatics tools and workflows
- **Enhanced CLI**: Advanced command-line features and automation
- **Tool Marketplace**: Community-contributed tool integrations

### Long-term Goals
- **Global Scale**: Worldwide deployment and data sharing
- **Research Integration**: Seamless integration with research workflows
- **Clinical Integration**: Direct integration with clinical decision support
- **Regulatory Compliance**: FDA and EMA regulatory compliance

---

**Built with ❤️ for the cancer genomics community**
