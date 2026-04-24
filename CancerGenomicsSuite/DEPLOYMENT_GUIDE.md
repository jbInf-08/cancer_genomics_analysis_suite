# Cancer Genomics Analysis Suite - Deployment Guide

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Infrastructure Setup](#infrastructure-setup)
4. [Application Deployment](#application-deployment)
5. [Configuration](#configuration)
6. [Monitoring and Alerting](#monitoring-and-alerting)
7. [Security](#security)
8. [Troubleshooting](#troubleshooting)
9. [Maintenance](#maintenance)

## Overview

The Cancer Genomics Analysis Suite is a comprehensive platform for cancer genomics analysis, featuring:

- **Real-time mutation detection and alerting**
- **Clinical data integration and processing**
- **Machine learning-based outcome prediction**
- **Multi-omics data analysis**
- **Pipeline orchestration with Snakemake/Nextflow**
- **Stream processing with Apache Kafka**
- **Graph database with Neo4j**
- **Comprehensive monitoring and alerting**

## Prerequisites

### System Requirements

- **Kubernetes Cluster**: Version 1.28+
- **Helm**: Version 3.12+
- **kubectl**: Latest version
- **Terraform**: Version 1.6+ (for infrastructure)
- **Docker**: Latest version
- **Git**: Latest version

### Cloud Provider Requirements

#### AWS
- AWS CLI configured
- EKS cluster with appropriate node groups
- RDS PostgreSQL instance
- ElastiCache Redis cluster
- S3 buckets for data storage
- Secrets Manager for secrets

#### GCP
- gcloud CLI configured
- GKE cluster with appropriate node pools
- Cloud SQL PostgreSQL instance
- Memorystore Redis instance
- Cloud Storage buckets
- Secret Manager for secrets

### Required Secrets

The following secrets must be configured in your cloud provider's secret management service:

#### Database Secrets
- `POSTGRES_PASSWORD`: Database password
- `POSTGRES_USER`: Database username
- `POSTGRES_DB`: Database name

#### Application Secrets
- `SECRET_KEY`: Flask secret key
- `JWT_SECRET_KEY`: JWT signing key
- `FLASK_SECRET_KEY`: Flask session key

#### Redis Secrets
- `REDIS_PASSWORD`: Redis password

#### Neo4j Secrets
- `NEO4J_PASSWORD`: Neo4j password
- `NEO4J_USERNAME`: Neo4j username
- `GDS_LICENSE_KEY`: Neo4j GDS license key (optional)

#### External API Keys
- `ENSEMBL_API_KEY`: Ensembl API key
- `UNIPROT_API_KEY`: UniProt API key
- `CLINVAR_API_KEY`: ClinVar API key
- `COSMIC_API_KEY`: COSMIC API key
- `NCBI_API_KEY`: NCBI API key

#### OAuth Credentials
- `GOOGLE_CLIENT_ID`: Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Google OAuth client secret
- `GITHUB_CLIENT_ID`: GitHub OAuth client ID
- `GITHUB_CLIENT_SECRET`: GitHub OAuth client secret

## Infrastructure Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/cancer-genomics-analysis-suite.git
cd cancer-genomics-analysis-suite
```

### 2. Configure Terraform

#### AWS Setup

```bash
cd terraform/aws
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:

```hcl
project_name = "cancer-genomics"
environment = "production"
aws_region = "us-west-2"
domain_name = "cancer-genomics.yourdomain.com"
kubernetes_version = "1.28"
kubernetes_namespace = "cancer-genomics"

# RDS Configuration
rds_instance_class = "db.r5.xlarge"
rds_allocated_storage = 500

# Redis Configuration
redis_node_type = "cache.r5.large"
redis_num_cache_nodes = 3

# EKS Configuration
eks_admin_users = [
  {
    userarn  = "arn:aws:iam::123456789012:user/admin"
    username = "admin"
    groups   = ["system:masters"]
  }
]
```

#### GCP Setup

```bash
cd terraform/gcp
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:

```hcl
project_name = "cancer-genomics"
environment = "production"
gcp_project_id = "your-project-id"
gcp_region = "us-central1"
domain_name = "cancer-genomics.yourdomain.com"
kubernetes_version = "1.28"
kubernetes_namespace = "cancer-genomics"

# Cloud SQL Configuration
cloud_sql_tier = "db-standard-4"
cloud_sql_disk_size = 500

# Redis Configuration
redis_tier = "STANDARD_HA"
redis_memory_size_gb = 8
```

### 3. Deploy Infrastructure

#### AWS

```bash
# Initialize Terraform
terraform init

# Plan the deployment
terraform plan

# Apply the configuration
terraform apply
```

#### GCP

```bash
# Initialize Terraform
terraform init

# Plan the deployment
terraform plan

# Apply the configuration
terraform apply
```

### 4. Configure kubectl

#### AWS

```bash
aws eks update-kubeconfig --region us-west-2 --name cancer-genomics-production-eks
```

#### GCP

```bash
gcloud container clusters get-credentials cancer-genomics-production-gke --region us-central1 --project your-project-id
```

## Application Deployment

### 1. Install ArgoCD

```bash
# Create ArgoCD namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for ArgoCD to be ready
kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd

# Get ArgoCD admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

### 2. Configure ArgoCD

```bash
# Port forward ArgoCD server
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Login to ArgoCD
argocd login localhost:8080 --username admin --password <admin-password>
```

### 3. Deploy the Application

```bash
# Create the ArgoCD project
kubectl apply -f argocd/argocd-project.yaml

# Deploy the main application
kubectl apply -f argocd/argocd-app.yaml

# Check deployment status
argocd app get cancer-genomics-analysis-suite
```

### 4. Alternative: Direct Helm Deployment

If you prefer to deploy directly with Helm:

```bash
# Add required Helm repositories
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add jetstack https://charts.jetstack.io
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Install cert-manager
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.13.0 \
  --set installCRDs=true

# Install the application
helm install cancer-genomics ./helm/cancer-genomics-analysis-suite \
  --namespace cancer-genomics \
  --create-namespace \
  --values ./helm/cancer-genomics-analysis-suite/values-production.yaml \
  --wait --timeout=10m
```

## Configuration

### 1. Environment-Specific Values

Create environment-specific values files:

#### values-dev.yaml
```yaml
global:
  environment: dev
  domain: dev.cancer-genomics.yourdomain.com
  apiDomain: api.dev.cancer-genomics.yourdomain.com

web:
  replicaCount: 1
  resources:
    limits:
      cpu: 500m
      memory: 1Gi
    requests:
      cpu: 100m
      memory: 256Mi

kafka:
  replicaCount: 1
  persistence:
    size: 20Gi

neo4j:
  replicaCount: 1
  persistence:
    dataSize: 20Gi
    logsSize: 5Gi
    importSize: 10Gi
```

#### values-staging.yaml
```yaml
global:
  environment: staging
  domain: staging.cancer-genomics.yourdomain.com
  apiDomain: api.staging.cancer-genomics.yourdomain.com

web:
  replicaCount: 2
  resources:
    limits:
      cpu: 1000m
      memory: 2Gi
    requests:
      cpu: 250m
      memory: 512Mi

kafka:
  replicaCount: 2
  persistence:
    size: 50Gi

neo4j:
  replicaCount: 1
  persistence:
    dataSize: 50Gi
    logsSize: 10Gi
    importSize: 20Gi
```

#### values-production.yaml
```yaml
global:
  environment: production
  domain: cancer-genomics.yourdomain.com
  apiDomain: api.cancer-genomics.yourdomain.com

web:
  replicaCount: 3
  resources:
    limits:
      cpu: 2000m
      memory: 4Gi
    requests:
      cpu: 500m
      memory: 1Gi

kafka:
  replicaCount: 3
  persistence:
    size: 100Gi

neo4j:
  replicaCount: 1
  persistence:
    dataSize: 100Gi
    logsSize: 20Gi
    importSize: 50Gi

monitoring:
  enabled: true
  alertmanager:
    email:
      critical: "critical-alerts@yourdomain.com"
      highImpact: "high-impact@yourdomain.com"
      pipeline: "pipeline-alerts@yourdomain.com"
      system: "system-alerts@yourdomain.com"
      security: "security-alerts@yourdomain.com"
      data: "data-alerts@yourdomain.com"
```

### 2. Secrets Configuration

#### Using SealedSecrets

```bash
# Install kubeseal
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.18.0/controller.yaml

# Create sealed secrets
kubeseal --fetch-cert > public.pem

# Seal your secrets
echo -n "your-secret-value" | kubeseal --raw --from-file=/dev/stdin --cert=public.pem
```

#### Using External Secrets Operator

```bash
# Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets -n external-secrets-system --create-namespace

# Create SecretStore
kubectl apply -f - <<EOF
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secrets-manager
  namespace: cancer-genomics
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-west-2
      auth:
        secretRef:
          accessKeyID:
            name: aws-credentials
            key: access-key-id
          secretAccessKey:
            name: aws-credentials
            key: secret-access-key
EOF

# Create ExternalSecret
kubectl apply -f - <<EOF
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: database-secrets
  namespace: cancer-genomics
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: database-secrets
    creationPolicy: Owner
  data:
  - secretKey: POSTGRES_PASSWORD
    remoteRef:
      key: cancer-genomics/database/password
      property: POSTGRES_PASSWORD
EOF
```

### 3. Ingress Configuration

#### AWS ALB Ingress Controller

```bash
# Install AWS Load Balancer Controller
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=cancer-genomics-production-eks \
  --set serviceAccount.create=false \
  --set region=us-west-2 \
  --set vpcId=vpc-xxxxxxxxx
```

#### GCP Ingress Controller

```bash
# Install GKE Ingress Controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml
```

## Monitoring and Alerting

### 1. Prometheus and Grafana

The monitoring stack is automatically deployed with the application. Access the dashboards:

- **Grafana**: https://grafana.cancer-genomics.yourdomain.com
- **Prometheus**: https://prometheus.cancer-genomics.yourdomain.com

### 2. Alert Configuration

Configure alert channels in the Alertmanager:

```yaml
# alertmanager-config.yaml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@yourdomain.com'
  smtp_auth_username: 'alerts@yourdomain.com'
  smtp_auth_password: 'your-app-password'

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'
  routes:
  - match:
      severity: critical
    receiver: 'critical-alerts'
  - match:
      severity: warning
    receiver: 'warning-alerts'

receivers:
- name: 'web.hook'
  webhook_configs:
  - url: 'http://127.0.0.1:5001/'

- name: 'critical-alerts'
  email_configs:
  - to: 'critical-alerts@yourdomain.com'
    subject: 'CRITICAL: {{ .GroupLabels.alertname }}'
    body: |
      {{ range .Alerts }}
      Alert: {{ .Annotations.summary }}
      Description: {{ .Annotations.description }}
      {{ end }}

- name: 'warning-alerts'
  email_configs:
  - to: 'warning-alerts@yourdomain.com'
    subject: 'WARNING: {{ .GroupLabels.alertname }}'
    body: |
      {{ range .Alerts }}
      Alert: {{ .Annotations.summary }}
      Description: {{ .Annotations.description }}
      {{ end }}
```

### 3. Custom Dashboards

Create custom Grafana dashboards for cancer genomics metrics:

```json
{
  "dashboard": {
    "title": "Cancer Genomics Analysis Suite",
    "panels": [
      {
        "title": "Mutation Detection Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(cancer_genomics_mutations_detected_total[5m])",
            "legendFormat": "Mutations/sec"
          }
        ]
      },
      {
        "title": "Pipeline Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(cancer_genomics_pipeline_successes_total[1h]) / rate(cancer_genomics_pipeline_attempts_total[1h])",
            "legendFormat": "Success Rate"
          }
        ]
      }
    ]
  }
}
```

## Security

### 1. Network Policies

```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: cancer-genomics-network-policy
  namespace: cancer-genomics
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8050
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
```

### 2. Pod Security Standards

```yaml
# pod-security-policy.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cancer-genomics
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

### 3. RBAC Configuration

```yaml
# rbac.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: cancer-genomics
  name: cancer-genomics-role
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps", "secrets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: cancer-genomics-rolebinding
  namespace: cancer-genomics
subjects:
- kind: ServiceAccount
  name: cancer-genomics-sa
  namespace: cancer-genomics
roleRef:
  kind: Role
  name: cancer-genomics-role
  apiGroup: rbac.authorization.k8s.io
```

## Troubleshooting

### 1. Common Issues

#### Pods Not Starting

```bash
# Check pod status
kubectl get pods -n cancer-genomics

# Check pod logs
kubectl logs -n cancer-genomics <pod-name>

# Check pod events
kubectl describe pod -n cancer-genomics <pod-name>
```

#### Database Connection Issues

```bash
# Check database connectivity
kubectl exec -it -n cancer-genomics <pod-name> -- psql -h postgresql -U postgres -d genomics_db

# Check database logs
kubectl logs -n cancer-genomics <postgres-pod-name>
```

#### Kafka Issues

```bash
# Check Kafka cluster status
kubectl exec -it -n cancer-genomics <kafka-pod-name> -- kafka-topics.sh --bootstrap-server localhost:9092 --list

# Check Kafka logs
kubectl logs -n cancer-genomics <kafka-pod-name>
```

### 2. Performance Issues

#### High Memory Usage

```bash
# Check resource usage
kubectl top pods -n cancer-genomics

# Check node resources
kubectl top nodes

# Scale up if needed
kubectl scale deployment cancer-genomics-web --replicas=5 -n cancer-genomics
```

#### Slow Database Queries

```bash
# Check database performance
kubectl exec -it -n cancer-genomics <postgres-pod-name> -- psql -U postgres -d genomics_db -c "SELECT * FROM pg_stat_activity;"

# Check slow queries
kubectl exec -it -n cancer-genomics <postgres-pod-name> -- psql -U postgres -d genomics_db -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
```

### 3. Log Analysis

#### Application Logs

```bash
# Stream logs from all pods
kubectl logs -f -l app.kubernetes.io/name=cancer-genomics-analysis-suite -n cancer-genomics

# Search for errors
kubectl logs -l app.kubernetes.io/name=cancer-genomics-analysis-suite -n cancer-genomics | grep -i error

# Check specific component logs
kubectl logs -l component=kafka-stream-processor -n cancer-genomics
```

#### System Logs

```bash
# Check node logs
kubectl get events --sort-by=.metadata.creationTimestamp -n cancer-genomics

# Check ingress logs
kubectl logs -n ingress-nginx <ingress-controller-pod>
```

## Maintenance

### 1. Regular Maintenance Tasks

#### Database Maintenance

```bash
# Create database backup
kubectl exec -it -n cancer-genomics <postgres-pod-name> -- pg_dump -U postgres genomics_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Vacuum database
kubectl exec -it -n cancer-genomics <postgres-pod-name> -- psql -U postgres -d genomics_db -c "VACUUM ANALYZE;"

# Update statistics
kubectl exec -it -n cancer-genomics <postgres-pod-name> -- psql -U postgres -d genomics_db -c "ANALYZE;"
```

#### Log Rotation

```bash
# Check log sizes
kubectl exec -it -n cancer-genomics <pod-name> -- du -sh /var/log/*

# Rotate logs
kubectl exec -it -n cancer-genomics <pod-name> -- logrotate -f /etc/logrotate.conf
```

#### Certificate Renewal

```bash
# Check certificate expiration
kubectl get certificates -n cancer-genomics

# Force certificate renewal
kubectl annotate certificate cancer-genomics-web-tls -n cancer-genomics cert-manager.io/renew-before="24h"
```

### 2. Updates and Upgrades

#### Application Updates

```bash
# Update application with new image
helm upgrade cancer-genomics ./helm/cancer-genomics-analysis-suite \
  --namespace cancer-genomics \
  --set image.tag=v1.2.0 \
  --wait --timeout=10m

# Rollback if needed
helm rollback cancer-genomics 1 -n cancer-genomics
```

#### Infrastructure Updates

```bash
# Update Terraform configuration
cd terraform/aws
terraform plan
terraform apply

# Update Kubernetes cluster
aws eks update-cluster-version --name cancer-genomics-production-eks --kubernetes-version 1.29
```

### 3. Backup and Recovery

#### Application Backup

```bash
# Backup application data
kubectl exec -it -n cancer-genomics <postgres-pod-name> -- pg_dump -U postgres genomics_db | gzip > genomics_backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Backup Neo4j data
kubectl exec -it -n cancer-genomics <neo4j-pod-name> -- neo4j-admin dump --database=genomics --to=/tmp/neo4j_backup.dump
kubectl cp cancer-genomics/<neo4j-pod-name>:/tmp/neo4j_backup.dump ./neo4j_backup_$(date +%Y%m%d_%H%M%S).dump
```

#### Disaster Recovery

```bash
# Restore from backup
kubectl exec -i -n cancer-genomics <postgres-pod-name> -- psql -U postgres genomics_db < backup_20240101_120000.sql

# Restore Neo4j data
kubectl cp ./neo4j_backup_20240101_120000.dump cancer-genomics/<neo4j-pod-name>:/tmp/neo4j_backup.dump
kubectl exec -it -n cancer-genomics <neo4j-pod-name> -- neo4j-admin load --database=genomics --from=/tmp/neo4j_backup.dump
```

### 4. Monitoring and Alerting Maintenance

#### Update Alert Rules

```bash
# Update Prometheus rules
kubectl apply -f monitoring/prometheus-rules.yaml

# Reload Prometheus configuration
kubectl exec -it -n monitoring <prometheus-pod-name> -- curl -X POST http://localhost:9090/-/reload
```

#### Update Dashboards

```bash
# Import new Grafana dashboard
kubectl exec -it -n monitoring <grafana-pod-name> -- curl -X POST \
  -H "Content-Type: application/json" \
  -d @dashboard.json \
  http://admin:admin@localhost:3000/api/dashboards/db
```

## Support

For support and questions:

- **Documentation**: [GitHub Wiki](https://github.com/your-org/cancer-genomics-analysis-suite/wiki)
- **Issues**: [GitHub Issues](https://github.com/your-org/cancer-genomics-analysis-suite/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/cancer-genomics-analysis-suite/discussions)
- **Email**: support@cancer-genomics.com

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.