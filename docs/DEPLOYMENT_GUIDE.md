# Cancer Genomics Analysis Suite - Deployment Guide

This guide covers deploying the Cancer Genomics Analysis Suite from development to production.

## Quick Start (Development)

### 1. Local Development Setup

```bash
# Clone and setup
git clone <repository-url>
cd cancer_genomics_analysis_suite

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -e .

# Copy environment configuration
cp .env.example .env
# Edit .env with your settings (on Windows, `copy .env.example .env` in cmd or PowerShell)
```

### 2. Start Database Services (Docker)

```bash
# Start PostgreSQL, Redis, and optionally Neo4j
docker compose -f docker/docker-compose.db.yml up -d

# Initialize the database
python scripts/setup_postgresql.py --update-env
```

### 3. Run the application

**Main product UI (Dash):** with the package installed (`pip install -e .` from repo root):

```bash
cancer-genomics
```

This serves the test route `GET /test` on the configured host and port (often `8050`).

**Flask application factory (REST / auth / dashboard routes) without Dash:**

```bash
python CancerGenomicsSuite/run_flask_app.py
```

**Note:** `python -m CancerGenomicsSuite.app` is not a supported one-liner for running the server (the `app` package is import-oriented). Use `run_flask_app.py` instead.

**Workflow example:**

```bash
python workflows/sample_analysis_workflow.py
```

## Production Deployment

### Prerequisites

- Kubernetes cluster (EKS, GKE, or AKS)
- kubectl configured
- Helm 3.x installed
- Docker registry access

### 1. Build Docker Image

```bash
# Build the application image
docker build -t cancer-genomics-suite:latest .

# Push to registry
docker tag cancer-genomics-suite:latest <registry>/cancer-genomics-suite:latest
docker push <registry>/cancer-genomics-suite:latest
```

### 2. Configure Helm Values

```bash
# Copy production values template
cp CancerGenomicsSuite/helm/cancer-genomics-analysis-suite/values-production.yaml \
   CancerGenomicsSuite/helm/cancer-genomics-analysis-suite/values-custom.yaml

# Edit values-custom.yaml with your configuration:
# - Database connection strings
# - API keys
# - Resource limits
# - Ingress settings
```

### 3. Deploy with Helm

```bash
# Create namespace
kubectl create namespace cancer-genomics

# Create secrets (API keys, database credentials)
kubectl create secret generic cancer-genomics-secrets \
  --namespace cancer-genomics \
  --from-env-file=.env.production

# Install the Helm chart
helm install cancer-genomics \
  ./CancerGenomicsSuite/helm/cancer-genomics-analysis-suite \
  --namespace cancer-genomics \
  --values ./CancerGenomicsSuite/helm/cancer-genomics-analysis-suite/values-custom.yaml
```

### 4. Deploy with ArgoCD (GitOps)

```bash
# Apply ArgoCD project and application
kubectl apply -f CancerGenomicsSuite/argocd/argocd-project.yaml
kubectl apply -f CancerGenomicsSuite/argocd/argocd-app.yaml
```

## Infrastructure Components

### Database (PostgreSQL)

```yaml
# values-custom.yaml
postgresql:
  enabled: true
  auth:
    username: cancer_genomics
    password: <secure-password>
    database: cancer_genomics
  primary:
    persistence:
      size: 100Gi
```

### Redis (Caching & Celery)

```yaml
redis:
  enabled: true
  auth:
    password: <secure-password>
  master:
    persistence:
      size: 10Gi
```

### Neo4j (Knowledge Graph)

```yaml
neo4j:
  enabled: true
  auth:
    username: neo4j
    password: <secure-password>
  persistence:
    size: 50Gi
```

### Kafka (Real-time Processing)

```yaml
kafka:
  enabled: true
  replicaCount: 3
  persistence:
    size: 50Gi
```

## Monitoring

### Prometheus & Grafana

The Helm chart includes Prometheus for metrics collection and Grafana dashboards for visualization.

```bash
# Access Grafana
kubectl port-forward svc/grafana 3000:3000 -n cancer-genomics

# Access Prometheus
kubectl port-forward svc/prometheus 9090:9090 -n cancer-genomics
```

### Alerting

Alert rules are configured in:
- `templates/alertmanager-rules.yaml`
- `grafana-alerting-rules.yaml`

## Scaling

### Horizontal Pod Autoscaler

```yaml
# values-custom.yaml
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
```

### Resource Limits

```yaml
resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: 2000m
    memory: 4Gi
```

## Security

### TLS/SSL

```yaml
ingress:
  enabled: true
  tls:
    - secretName: cancer-genomics-tls
      hosts:
        - cancer-genomics.example.com
```

### Network Policies

Network policies are defined in `templates/networkpolicy.yaml` to restrict pod-to-pod communication.

### Secrets Management

For production, use:
- Kubernetes Secrets with encryption at rest
- HashiCorp Vault integration (see `templates/vault-integration.yaml`)
- Sealed Secrets (see `templates/sealed-secrets.yaml`)

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n cancer-genomics
kubectl describe pod <pod-name> -n cancer-genomics
kubectl logs <pod-name> -n cancer-genomics
```

### Database Connection

```bash
# Port forward to PostgreSQL
kubectl port-forward svc/postgresql 5432:5432 -n cancer-genomics

# Connect
psql -h localhost -U cancer_genomics -d cancer_genomics
```

### Common Issues

1. **Pod CrashLoopBackOff**: Check logs for application errors
2. **Database connection refused**: Verify secrets and service names
3. **Out of memory**: Increase resource limits
4. **Ingress not working**: Check ingress controller and TLS certificates

## Environment-Specific Configuration

| Environment | Values File | Notes |
|-------------|-------------|-------|
| Development | values-dev.yaml | Single replica, minimal resources |
| Staging | values-staging.yaml | Production-like, smaller scale |
| Production | values-production.yaml | Full HA, monitoring, autoscaling |

## Backup and Recovery

### Database Backups

```bash
# Create backup
pg_dump -h localhost -U cancer_genomics cancer_genomics > backup.sql

# Restore backup
psql -h localhost -U cancer_genomics cancer_genomics < backup.sql
```

### Persistent Volume Backups

Use your cloud provider's volume snapshot feature or Velero for cross-cluster backups.

---

For more information, see the project README and individual component documentation.
