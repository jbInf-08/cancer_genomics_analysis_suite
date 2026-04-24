# Complete Deployment Guide - Cancer Genomics Analysis Suite

This guide provides comprehensive instructions for deploying the Cancer Genomics Analysis Suite with all the implemented features.

## 🚀 Implemented Features

### ✅ Infrastructure as Code (Terraform)
- **AWS EKS** cluster with VPC, subnets, and security groups
- **GCP GKE** cluster with networking and security
- **S3/GCS** buckets for artifact storage
- **IAM roles** and service accounts for cloud integration
- **Resource management** with proper tagging and naming

### ✅ Ingress + TLS with cert-manager
- **NGINX Ingress Controller** with load balancing
- **Let's Encrypt** certificates for automatic SSL/TLS
- **AWS Certificate Manager** integration
- **GCP Certificate Manager** integration
- **Security headers** and rate limiting

### ✅ AWS/GCP Secrets Integration
- **AWS Secrets Manager CSI Driver** for secret injection
- **GCP Secret Manager CSI Driver** for secret injection
- **SecretProviderClass** configurations
- **Automatic secret rotation** and management
- **RBAC** for secret access control

### ✅ S3/GCS Artifact Support
- **Unified storage interface** for cloud providers
- **S3 client** with full feature support
- **GCS client** with full feature support
- **Storage factory** for provider selection
- **Artifact management** for workflows

### ✅ Helm Templates
- **Comprehensive Helm chart** with all components
- **Environment-specific values** (dev, staging, prod)
- **Cloud provider configurations**
- **Resource limits** and requests
- **Health checks** and monitoring

### ✅ ArgoCD GitOps Setup
- **Complete ArgoCD configuration**
- **Project management** with RBAC
- **Application definitions** for all components
- **Sync windows** and policies
- **Notification integration** (Slack, email, webhooks)

## 📋 Prerequisites

### Required Tools
- **kubectl** (v1.28+)
- **helm** (v3.12+)
- **terraform** (v1.0+)
- **docker** (v20.10+)
- **git** (v2.30+)

### Cloud Provider Access
- **AWS**: IAM user with EKS, S3, and Secrets Manager permissions
- **GCP**: Service account with GKE, GCS, and Secret Manager permissions
- **Domain**: DNS control for certificate validation

### Required Secrets
- **Database passwords** (PostgreSQL, Redis)
- **Application secrets** (JWT, API keys)
- **Cloud credentials** (AWS, GCP)
- **SSL certificates** (if not using Let's Encrypt)

## 🏗️ Deployment Steps

### Step 1: Infrastructure Provisioning

#### AWS Deployment
```bash
# Navigate to terraform directory
cd terraform

# Copy and configure variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# Initialize Terraform
terraform init

# Plan the deployment
terraform plan

# Apply the infrastructure
terraform apply
```

#### GCP Deployment
```bash
# Set GCP project
export GOOGLE_CLOUD_PROJECT=your-project-id

# Authenticate with GCP
gcloud auth login
gcloud auth application-default login

# Initialize and apply
terraform init
terraform plan
terraform apply
```

### Step 2: Kubernetes Cluster Setup

#### Configure kubectl
```bash
# AWS EKS
aws eks update-kubeconfig --region us-west-2 --name cancer-genomics-prod

# GCP GKE
gcloud container clusters get-credentials cancer-genomics-prod --region us-central1
```

#### Install Required Components
```bash
# Install NGINX Ingress Controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace

# Install cert-manager
helm repo add jetstack https://charts.jetstack.io
helm repo update
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true
```

### Step 3: Secrets Management Setup

#### AWS Secrets Manager
```bash
# Create secrets in AWS Secrets Manager
aws secretsmanager create-secret \
  --name "cancer-genomics/database/password" \
  --description "PostgreSQL password" \
  --secret-string "your-postgres-password"

aws secretsmanager create-secret \
  --name "cancer-genomics/redis/password" \
  --description "Redis password" \
  --secret-string "your-redis-password"

# Deploy AWS Secrets Manager CSI Driver
kubectl apply -f k8s/aws-secrets.yaml
```

#### GCP Secret Manager
```bash
# Create secrets in GCP Secret Manager
gcloud secrets create cancer-genomics-database-password \
  --data-file=- <<< "your-postgres-password"

gcloud secrets create cancer-genomics-redis-password \
  --data-file=- <<< "your-redis-password"

# Deploy GCP Secret Manager CSI Driver
kubectl apply -f k8s/gcp-secrets.yaml
```

### Step 4: Storage Setup

#### S3 Bucket (AWS)
```bash
# Create S3 bucket for artifacts
aws s3 mb s3://cancer-genomics-artifacts
aws s3api put-bucket-versioning \
  --bucket cancer-genomics-artifacts \
  --versioning-configuration Status=Enabled
```

#### GCS Bucket (GCP)
```bash
# Create GCS bucket for artifacts
gsutil mb gs://cancer-genomics-artifacts
gsutil versioning set on gs://cancer-genomics-artifacts
```

### Step 5: ArgoCD Installation and Configuration

#### Install ArgoCD
```bash
# Create ArgoCD namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for ArgoCD to be ready
kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd
```

#### Configure ArgoCD
```bash
# Apply ArgoCD configuration
kubectl apply -f argocd/argocd-config.yaml

# Apply ArgoCD project
kubectl apply -f argocd/argocd-project.yaml

# Apply ArgoCD applications
kubectl apply -f argocd/argocd-app.yaml
```

### Step 6: Application Deployment

#### Deploy via ArgoCD
```bash
# Check ArgoCD application status
kubectl get applications -n argocd

# Access ArgoCD UI
kubectl port-forward svc/argocd-server -n argocd 8080:443
# Open https://localhost:8080 in browser
```

#### Deploy via Helm (Alternative)
```bash
# Add Helm repository
helm repo add cancer-genomics ./helm/cancer-genomics-analysis-suite

# Deploy the application
helm install cancer-genomics cancer-genomics/cancer-genomics-analysis-suite \
  --namespace cancer-genomics \
  --create-namespace \
  --values helm/cancer-genomics-analysis-suite/values-prod.yaml
```

## 🔧 Configuration

### Environment Variables

Update the following in your Helm values or ArgoCD applications:

```yaml
global:
  domain: "cancer-genomics.yourdomain.com"
  apiDomain: "api.cancer-genomics.yourdomain.com"
  cloudProvider: "aws"  # or "gcp"
  aws:
    s3Bucket: "cancer-genomics-artifacts"
    secretsManager:
      enabled: true
  gcp:
    gcsBucket: "cancer-genomics-artifacts"
    secretManager:
      enabled: true
```

### DNS Configuration

Configure your DNS to point to the load balancer:

```bash
# Get load balancer IP
kubectl get svc ingress-nginx-controller -n ingress-nginx

# Create DNS records
# A record: cancer-genomics.yourdomain.com -> <load-balancer-ip>
# A record: api.cancer-genomics.yourdomain.com -> <load-balancer-ip>
# A record: argocd.cancer-genomics.yourdomain.com -> <load-balancer-ip>
```

## 📊 Monitoring and Observability

### Prometheus and Grafana
```bash
# Install monitoring stack
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

### Application Monitoring
- **Health checks** at `/health` endpoint
- **Metrics** at `/metrics` endpoint
- **Logs** via centralized logging
- **Alerts** via Prometheus and ArgoCD

## 🔒 Security

### Network Policies
```bash
# Apply network policies
kubectl apply -f k8s/network-policies.yaml
```

### Pod Security Standards
```bash
# Enable Pod Security Standards
kubectl label namespace cancer-genomics pod-security.kubernetes.io/enforce=restricted
```

### RBAC
- **Service accounts** with minimal permissions
- **Role-based access** for different environments
- **Secret access** via cloud providers

## 🚨 Troubleshooting

### Common Issues

1. **Certificate Issues**
   ```bash
   # Check certificate status
   kubectl get certificates -n cancer-genomics
   kubectl describe certificate cancer-genomics-tls -n cancer-genomics
   ```

2. **Ingress Issues**
   ```bash
   # Check ingress status
   kubectl get ingress -n cancer-genomics
   kubectl describe ingress cancer-genomics-ingress -n cancer-genomics
   ```

3. **Secret Issues**
   ```bash
   # Check secret provider class
   kubectl get secretproviderclass -n cancer-genomics
   kubectl describe secretproviderclass aws-secrets-manager-spc -n cancer-genomics
   ```

4. **ArgoCD Issues**
   ```bash
   # Check ArgoCD application status
   kubectl get applications -n argocd
   kubectl describe application cancer-genomics-analysis-suite -n argocd
   ```

### Debug Commands

```bash
# Check pod logs
kubectl logs -n cancer-genomics deployment/cancer-genomics-web

# Check service status
kubectl get svc -n cancer-genomics

# Check ingress controller logs
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager
```

## 📈 Scaling and Performance

### Horizontal Pod Autoscaling
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: cancer-genomics-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cancer-genomics-web
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### Resource Optimization
- **CPU requests**: 500m
- **Memory requests**: 1Gi
- **CPU limits**: 2000m
- **Memory limits**: 4Gi

## 🔄 CI/CD Integration

### GitHub Actions
```yaml
name: Deploy to Kubernetes
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Deploy to ArgoCD
      run: |
        # Trigger ArgoCD sync
        argocd app sync cancer-genomics-analysis-suite
```

### GitLab CI
```yaml
deploy:
  stage: deploy
  script:
    - argocd app sync cancer-genomics-analysis-suite
  only:
    - main
```

## 📚 Additional Resources

- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest)
- [Terraform GCP Provider](https://registry.terraform.io/providers/hashicorp/google/latest)
- [Helm Documentation](https://helm.sh/docs/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

## 🎯 Next Steps

1. **Set up monitoring** and alerting
2. **Configure backup** strategies
3. **Implement disaster recovery**
4. **Set up CI/CD pipelines**
5. **Configure security scanning**
6. **Implement cost optimization**

## 📞 Support

For issues and questions:
- Check the troubleshooting section above
- Review application logs
- Check ArgoCD sync status
- Verify cloud provider permissions
- Ensure DNS configuration is correct

---

**Congratulations!** 🎉 You have successfully deployed the Cancer Genomics Analysis Suite with enterprise-grade infrastructure, security, and monitoring capabilities.
