# Terraform Infrastructure as Code for Cancer Genomics Analysis Suite

This directory contains Terraform configurations for deploying the Cancer Genomics Analysis Suite infrastructure on both AWS and GCP cloud platforms.

## Overview

The Terraform configuration provides:
- **Multi-cloud support**: AWS (EKS) and GCP (GKE)
- **Production-ready infrastructure**: Databases, caching, monitoring, security
- **GitOps integration**: ArgoCD for continuous deployment
- **Security**: Network policies, IAM roles, encryption
- **Monitoring**: Prometheus, Grafana, CloudWatch/Cloud Monitoring
- **High availability**: Multi-AZ deployments, auto-scaling

## Architecture

### AWS Architecture
- **EKS Cluster**: Managed Kubernetes with auto-scaling node groups
- **RDS PostgreSQL**: Managed database with Multi-AZ deployment
- **ElastiCache Redis**: Managed Redis cluster with replication
- **Application Load Balancer**: With WAF protection
- **Route 53**: DNS management
- **CloudWatch**: Monitoring and alerting
- **S3**: Object storage for artifacts

### GCP Architecture
- **GKE Cluster**: Managed Kubernetes with auto-scaling
- **Cloud SQL PostgreSQL**: Managed database with high availability
- **Memorystore Redis**: Managed Redis with replication
- **Cloud Load Balancing**: Global load balancer
- **Cloud DNS**: DNS management
- **Cloud Monitoring**: Monitoring and alerting
- **Cloud Storage**: Object storage for artifacts

## Prerequisites

### General Requirements
- Terraform >= 1.0
- kubectl
- helm
- AWS CLI (for AWS deployment)
- gcloud CLI (for GCP deployment)

### AWS Requirements
- AWS account with appropriate permissions
- AWS CLI configured with credentials
- Domain name for Route 53 (optional)

### GCP Requirements
- GCP project with billing enabled
- gcloud CLI configured with credentials
- Domain name for Cloud DNS (optional)

## Quick Start

### 1. Clone and Setup
```bash
git clone <repository-url>
cd CancerGenomicsSuite/terraform
```

### 2. Configure Variables
```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

### 3. Initialize Terraform
```bash
terraform init
```

### 4. Plan Deployment
```bash
terraform plan
```

### 5. Deploy Infrastructure
```bash
terraform apply
```

## Configuration

### Environment Variables
Set the following environment variables:

```bash
# For AWS
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-west-2"

# For GCP
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"
export GOOGLE_PROJECT="your-project-id"
```

### Terraform Variables
Key variables in `terraform.tfvars`:

```hcl
# General
environment = "prod"
project_name = "cancer-genomics-analysis-suite"

# AWS Configuration
aws_region = "us-west-2"
aws_availability_zones = ["us-west-2a", "us-west-2b", "us-west-2c"]
aws_instance_type = "t3.medium"
aws_node_count = 3

# GCP Configuration
gcp_project_id = "your-project-id"
gcp_region = "us-central1"
gcp_machine_type = "e2-standard-2"
gcp_node_count = 3

# Domain Configuration
domain_name = "cancer-genomics.yourdomain.com"
api_domain_name = "api.cancer-genomics.yourdomain.com"

# Storage
s3_bucket_name = "cancer-genomics-artifacts"
gcs_bucket_name = "cancer-genomics-artifacts"

# Security
enable_aws_secrets_manager = true
enable_gcp_secret_manager = true
enable_network_policies = true
enable_pod_security_policies = true

# Monitoring
enable_monitoring = true
enable_logging = true

# GitOps
enable_argocd = true
argocd_repo_url = "https://github.com/your-org/cancer-genomics-analysis-suite"
```

## Deployment Options

### AWS Only
```bash
terraform apply -target=aws_eks_cluster.cancer_genomics
terraform apply -target=aws_db_instance.postgres
terraform apply -target=aws_elasticache_replication_group.redis
```

### GCP Only
```bash
terraform apply -target=google_container_cluster.cancer_genomics
terraform apply -target=google_sql_database_instance.postgres
terraform apply -target=google_redis_instance.redis
```

### Full Stack
```bash
terraform apply
```

## Post-Deployment

### 1. Configure kubectl
```bash
# For AWS
aws eks update-kubeconfig --region us-west-2 --name cancer-genomics-prod-<suffix>

# For GCP
gcloud container clusters get-credentials cancer-genomics-prod-<suffix> --region us-central1
```

### 2. Verify Deployment
```bash
kubectl get nodes
kubectl get pods -n cancer-genomics
kubectl get services -n cancer-genomics
```

### 3. Access Applications
- **Main Application**: https://cancer-genomics.yourdomain.com
- **API**: https://api.cancer-genomics.yourdomain.com
- **ArgoCD**: https://argocd.cancer-genomics.yourdomain.com
- **Grafana**: https://grafana.cancer-genomics.yourdomain.com

## Security Features

### Network Security
- VPC with private subnets
- Security groups with least privilege
- Network policies for pod-to-pod communication
- WAF protection (AWS) / Cloud Armor (GCP)

### Data Security
- Encryption at rest and in transit
- Secrets management integration
- RBAC with service accounts
- Pod security policies

### Access Control
- IAM roles with minimal permissions
- Service account authentication
- OIDC integration with Keycloak

## Monitoring and Observability

### Metrics
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **CloudWatch/Cloud Monitoring**: Cloud-native monitoring

### Logging
- **ELK Stack**: Centralized logging
- **CloudWatch Logs/Cloud Logging**: Cloud-native logging
- **Fluentd**: Log aggregation

### Alerting
- **Alertmanager**: Alert routing and management
- **SNS/Cloud Pub/Sub**: Notification delivery
- **PagerDuty**: Incident management integration

## Backup and Disaster Recovery

### Database Backups
- **RDS**: Automated backups with point-in-time recovery
- **Cloud SQL**: Automated backups with point-in-time recovery
- **Cross-region replication**: For disaster recovery

### Application Backups
- **S3/Cloud Storage**: Application artifacts and data
- **Cross-region replication**: For disaster recovery
- **Versioning**: Object versioning for rollback capability

## Cost Optimization

### Resource Sizing
- Right-sized instances based on usage
- Auto-scaling for dynamic workloads
- Spot instances for non-critical workloads

### Storage Optimization
- Lifecycle policies for old data
- Compression and deduplication
- Appropriate storage classes

### Monitoring Costs
- Cost allocation tags
- Budget alerts
- Regular cost reviews

## Troubleshooting

### Common Issues

#### 1. Terraform State Issues
```bash
terraform refresh
terraform plan
```

#### 2. Kubernetes Connection Issues
```bash
kubectl cluster-info
kubectl get nodes
```

#### 3. Application Deployment Issues
```bash
kubectl describe pod <pod-name> -n cancer-genomics
kubectl logs <pod-name> -n cancer-genomics
```

#### 4. Database Connection Issues
```bash
kubectl get secrets -n cancer-genomics
kubectl describe secret db-credentials -n cancer-genomics
```

### Useful Commands
```bash
# Check Terraform state
terraform state list
terraform state show <resource>

# Check Kubernetes resources
kubectl get all -n cancer-genomics
kubectl describe ingress -n cancer-genomics

# Check Helm releases
helm list -A
helm status cancer-genomics-analysis-suite -n cancer-genomics

# Check ArgoCD applications
kubectl get applications -n argocd
```

## Maintenance

### Regular Tasks
- Update Terraform and provider versions
- Review and update security policies
- Monitor resource utilization
- Review and update backup policies
- Update application versions

### Scaling
- Horizontal Pod Autoscaling (HPA)
- Vertical Pod Autoscaling (VPA)
- Cluster Autoscaling
- Database scaling

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review Terraform and Kubernetes documentation
3. Check application logs and metrics
4. Contact the development team

## Contributing

1. Follow Terraform best practices
2. Use consistent naming conventions
3. Document all changes
4. Test in development environment first
5. Submit pull requests for review
