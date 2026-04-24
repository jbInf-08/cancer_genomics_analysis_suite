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

### Method 1: PyPI Installation (Recommended)

The easiest way to install the Cancer Genomics Analysis Suite is using pip:

```bash
# Install the latest version
pip install cancer-genomics-analysis-suite

# Install with optional dependencies
pip install cancer-genomics-analysis-suite[dev,test,docs]

# Install specific version
pip install cancer-genomics-analysis-suite==1.0.0
```

### Method 2: Source Installation

For development or custom configurations:

```bash
# Clone the repository
git clone https://github.com/your-org/cancer-genomics-analysis-suite.git
cd cancer-genomics-analysis-suite

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Install development dependencies
pip install -e ".[dev,test,docs]"
```

### Method 3: Docker Installation

For containerized deployment:

```bash
# Pull the official image
docker pull ghcr.io/your-org/cancer-genomics-analysis-suite:latest

# Run the container
docker run -d \
  --name cancer-genomics \
  -p 8080:8080 \
  -v $(pwd)/data:/app/data \
  ghcr.io/your-org/cancer-genomics-analysis-suite:latest
```

### Method 4: Kubernetes Installation

For production deployment:

```bash
# Add Helm repository
helm repo add cancer-genomics https://your-org.github.io/cancer-genomics-analysis-suite
helm repo update

# Install with default values
helm install cancer-genomics cancer-genomics/cancer-genomics-analysis-suite

# Install with custom values
helm install cancer-genomics cancer-genomics/cancer-genomics-analysis-suite \
  --values values-production.yaml
```

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

### Environment Variables

Create a `.env` file in your project directory:

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

### Configuration Files

Create configuration files for different environments:

#### Development Configuration (`config/development.yaml`)

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

### Basic Verification

Test the installation:

```bash
# Check version
cancer-genomics --version

# Run basic health check
cancer-genomics health-check

# Test CLI tools
cancer-genomics-cli --help
```

### Python Verification

```python
# Test Python import
import CancerGenomicsSuite
print(CancerGenomicsSuite.__version__)

# Test basic functionality
from CancerGenomicsSuite.modules.mutation_analysis import MutationAnalyzer
analyzer = MutationAnalyzer()
print("MutationAnalyzer imported successfully")
```

### Docker Verification

```bash
# Check container status
docker ps | grep cancer-genomics

# Check logs
docker logs cancer-genomics

# Test API endpoint
curl http://localhost:8080/health
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
2. **Search issues**: Check [GitHub Issues](https://github.com/your-org/cancer-genomics-analysis-suite/issues)
3. **Community support**: Ask questions in [GitHub Discussions](https://github.com/your-org/cancer-genomics-analysis-suite/discussions)
4. **Documentation**: Refer to the [troubleshooting guide](reference/troubleshooting.md)

### Support Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and community support
- **Email**: support@cancer-genomics.com
- **Slack**: #cancer-genomics channel

---

**Next Steps**: After installation, proceed to the [Quick Start Guide](quick_start.md) to begin using the system.
