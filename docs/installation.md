# Installation Guide

This guide provides comprehensive instructions for installing the Cancer Genomics Analysis Suite on various platforms and environments.

## Table of Contents

- [System Requirements](#system-requirements)
- [Installation Methods](#installation-methods)
- [Platform-Specific Instructions](#platform-specific-instructions)
- [Configuration](#configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements

- **Operating System**: Linux (Ubuntu 20.04+), macOS (10.15+), or Windows 10+
- **Python**: 3.8 or higher
- **Memory**: 8 GB RAM (16 GB recommended)
- **Storage**: 50 GB free space (100 GB recommended)
- **CPU**: 4 cores (8 cores recommended)

### Recommended Requirements

- **Operating System**: Linux (Ubuntu 22.04 LTS)
- **Python**: 3.11 or higher
- **Memory**: 32 GB RAM
- **Storage**: 500 GB SSD
- **CPU**: 16 cores
- **GPU**: NVIDIA GPU with CUDA support (optional, for ML workloads)

### Dependencies

- **Docker**: 20.10+ (for containerized deployment)
- **Kubernetes**: 1.28+ (for production deployment)
- **Helm**: 3.12+ (for Kubernetes deployment)
- **Terraform**: 1.6+ (for infrastructure provisioning)

## Installation Methods

### Method 1: PyPI (when published)

The project is defined in `pyproject.toml` as `cancer-genomics-analysis-suite`. If a matching release is published to PyPI, you can use:

```bash
pip install cancer-genomics-analysis-suite[dev,test,docs]
```

**Recommended for day-to-day work:** install **from a clone** (Method 2) so paths and the latest tree match the documentation in this repo.

### Method 2: Source installation (recommended)

For development or custom configurations:

```bash
# Clone the repository
git clone https://github.com/jbInf-08/cancer_genomics_analysis_suite.git
cd cancer_genomics_analysis_suite

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Install development dependencies
pip install -e ".[dev,test,docs]"
```

### Method 3: Docker

There is no single mandatory image name in this repo. Build and run from your own registry, or use compose files under `docker/` and `CancerGenomicsSuite/` (see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)) for local stacks (e.g. database services).

### Method 4: Kubernetes (Helm from this repository)

The Helm chart ships in-tree at `CancerGenomicsSuite/helm/cancer-genomics-analysis-suite/`. From the **repository root**:

```bash
helm install cancer-genomics ./CancerGenomicsSuite/helm/cancer-genomics-analysis-suite \
  --namespace cancer-genomics --create-namespace \
  -f ./CancerGenomicsSuite/helm/cancer-genomics-analysis-suite/values.yaml
```

See [LOCAL_HELM_QUICKSTART.md](LOCAL_HELM_QUICKSTART.md) and [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for details. ArgoCD manifests are under `CancerGenomicsSuite/argocd/`.

## Platform-Specific Instructions

### Ubuntu/Debian

```bash
# Update package list
sudo apt update

# Install system dependencies
sudo apt install -y python3 python3-pip python3-venv git curl

# Install Python dependencies
pip3 install cancer-genomics-analysis-suite

# Install system packages for bioinformatics tools
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev
```

### CentOS/RHEL/Fedora

```bash
# Install system dependencies
sudo yum install -y python3 python3-pip git curl

# Install Python dependencies
pip3 install cancer-genomics-analysis-suite

# Install development tools
sudo yum groupinstall -y "Development Tools"
```

### macOS

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install system dependencies
brew install python3 git curl

# Install Python dependencies
pip3 install cancer-genomics-analysis-suite
```

### Windows

```powershell
# Install Python from python.org or Microsoft Store
# Install Git from git-scm.com

# Open PowerShell as Administrator
# Install Python dependencies
pip install cancer-genomics-analysis-suite

# Install Windows-specific dependencies
pip install pywin32
```

## Configuration

For local development, copy the root **`.env.example`** to **`.env`** in the repository root, or start from [CancerGenomicsSuite/environment.template](../CancerGenomicsSuite/environment.template) (advanced: [CancerGenomicsSuite/environment.advanced.template](../CancerGenomicsSuite/environment.advanced.template)).

The snippets below are illustrative; the canonical variable names and defaults are in `.env.example` and `CancerGenomicsSuite/config/`.

### Environment variables

Set values in **`.env`** (or the environment) as needed, for example:

```bash
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/cancer_genomics
REDIS_URL=redis://localhost:6379/0

# External APIs
ENSEMBL_API_KEY=your_ensembl_key
UNIPROT_API_KEY=your_uniprot_key
CLINVAR_API_KEY=your_clinvar_key

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password

# Security
SECRET_KEY=your_secret_key
JWT_SECRET_KEY=your_jwt_secret

# Monitoring
PROMETHEUS_ENDPOINT=http://localhost:9090
GRAFANA_ENDPOINT=http://localhost:3000
```

### Optional YAML configuration

If you use YAML for environments, you can mirror patterns like the following; the app primarily uses [CancerGenomicsSuite/config/settings.py](../CancerGenomicsSuite/config/settings.py) and environment variables.

#### Development configuration (example: `config/development.yaml`)

```yaml
app:
  debug: true
  host: localhost
  port: 8080

database:
  url: postgresql://localhost:5432/cancer_genomics_dev
  echo: true

logging:
  level: DEBUG
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

cache:
  type: redis
  url: redis://localhost:6379/0
  ttl: 3600
```

#### Production Configuration (`config/production.yaml`)

```yaml
app:
  debug: false
  host: 0.0.0.0
  port: 8080

database:
  url: postgresql://user:password@db-host:5432/cancer_genomics
  echo: false
  pool_size: 20
  max_overflow: 30

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: /var/log/cancer-genomics/app.log

cache:
  type: redis
  url: redis://redis-host:6379/0
  ttl: 3600
  cluster: true

security:
  secret_key: ${SECRET_KEY}
  jwt_secret: ${JWT_SECRET_KEY}
  cors_origins: ["https://yourdomain.com"]
```

## Verification

### Basic checks

```bash
# After pip install -e . — package version
python -c "import CancerGenomicsSuite; print(CancerGenomicsSuite.__version__)"

# With the dashboard running (default port often 8050) — test route
curl -s http://127.0.0.1:8050/test

# Bioinformatics CLI
cancer-genomics-cli --help
```

Start the main Dash app with: **`cancer-genomics`** (see `pyproject.toml` console scripts), or from the `CancerGenomicsSuite` directory: `python main_dashboard.py`. For the Flask app factory only, use: `python CancerGenomicsSuite/run_flask_app.py`.

### Python verification

```python
# Test Python import
import CancerGenomicsSuite
print(CancerGenomicsSuite.__version__)

# Test basic functionality
from CancerGenomicsSuite.modules.mutation_analysis import MutationAnalyzer
analyzer = MutationAnalyzer()
print("MutationAnalyzer imported successfully")
```

### Docker verification

If you use a container, adjust name and port to your compose or run command, then e.g.:

```bash
docker ps
docker logs <container>
curl http://localhost:<port>/test   # Dash test route, if exposed
```

### Kubernetes Verification

```bash
# Check pod status
kubectl get pods -n cancer-genomics

# Check service status
kubectl get services -n cancer-genomics

# Check ingress
kubectl get ingress -n cancer-genomics
```

## Troubleshooting

### Common Issues

#### Python Import Errors

```bash
# Check Python version
python --version

# Check installed packages
pip list | grep cancer-genomics

# Reinstall if necessary
pip uninstall cancer-genomics-analysis-suite
pip install cancer-genomics-analysis-suite
```

#### Database Connection Issues

```bash
# Check database status
pg_isready -h localhost -p 5432

# Test connection
psql -h localhost -p 5432 -U username -d cancer_genomics -c "SELECT 1;"

# Check environment variables
echo $DATABASE_URL
```

#### Docker Issues

```bash
# Check Docker status
docker info

# Check image
docker images | grep cancer-genomics

# Rebuild if necessary
docker build -t cancer-genomics-analysis-suite .
```

#### Kubernetes Issues

```bash
# Check cluster status
kubectl cluster-info

# Check namespace
kubectl get namespaces | grep cancer-genomics

# Check resources
kubectl get all -n cancer-genomics
```

### Performance Issues

#### Memory Issues

```bash
# Check memory usage
free -h

# Monitor memory usage
htop

# Increase swap if needed
sudo swapon --show
```

#### Disk Space Issues

```bash
# Check disk usage
df -h

# Clean up old files
docker system prune -a

# Check log files
du -sh /var/log/cancer-genomics/
```

### Network Issues

#### Port Conflicts

```bash
# Check port usage
netstat -tulpn | grep :8080

# Kill process using port
sudo kill -9 $(lsof -t -i:8080)

# Use different port
export PORT=8081
```

#### Firewall Issues

```bash
# Check firewall status
sudo ufw status

# Allow port
sudo ufw allow 8080

# Check iptables
sudo iptables -L
```

### Getting Help

If you encounter issues not covered in this guide:

1. **Check the logs**: Look at application logs for error messages
2. **Search issues:** [cancer_genomics_analysis_suite on GitHub](https://github.com/jbInf-08/cancer_genomics_analysis_suite/issues)
3. **Documentation:** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) and the root [README.md](../README.md)

### Support Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and community support
- **Email**: support@cancer-genomics.com
- **Slack**: #cancer-genomics channel

---

**Next steps:** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md), [LOCAL_HELM_QUICKSTART.md](LOCAL_HELM_QUICKSTART.md), and the root [README.md](../README.md).
