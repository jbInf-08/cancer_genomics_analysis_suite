# Deployment Scripts

This directory contains deployment scripts and configurations for the Cancer Genomics Analysis Suite across different cloud platforms.

## Directory Structure

```
scripts/deploy/
├── README.md                           # This file
├── aws-deploy.sh                       # AWS deployment script
├── gcp-deploy.sh                       # GCP deployment script
├── aws-lb-controller-policy.json       # AWS Load Balancer Controller IAM policy
├── ebs-csi-policy.json                 # AWS EBS CSI Driver IAM policy
└── gcs-lifecycle.json                  # GCS bucket lifecycle configuration
```

## Prerequisites

### General Requirements

- **Kubernetes Cluster**: Version 1.24 or higher
- **Helm**: Version 3.12 or higher
- **kubectl**: Version 1.24 or higher
- **Docker**: For building and pushing images

### Cloud-Specific Requirements

#### AWS
- AWS CLI configured with appropriate permissions
- EKS cluster with worker nodes
- IAM roles for service accounts (IRSA) enabled
- VPC with public/private subnets

#### GCP
- gcloud CLI configured with appropriate permissions
- GKE cluster with Workload Identity enabled
- GCP project with billing enabled
- Required APIs enabled

## AWS Deployment

### Prerequisites

1. **AWS CLI Configuration**:
   ```bash
   aws configure
   ```

2. **EKS Cluster**:
   ```bash
   # Create EKS cluster (if not exists)
   eksctl create cluster \
     --name cancer-genomics-prod \
     --region us-west-2 \
     --nodegroup-name workers \
     --node-type t3.medium \
     --nodes 3 \
     --nodes-min 1 \
     --nodes-max 5 \
     --managed
   ```

3. **Required IAM Permissions**:
   - EKS cluster access
   - IAM role creation
   - EC2 instance management
   - Load balancer management
   - EBS volume management
   - EFS file system management

### Deployment

#### Automated Deployment

```bash
# Make script executable
chmod +x aws-deploy.sh

# Deploy to AWS
./aws-deploy.sh \
  --cluster-name cancer-genomics-prod \
  --region us-west-2 \
  --environment production \
  --image-tag v1.0.0
```

#### Manual Deployment Steps

1. **Update kubeconfig**:
   ```bash
   aws eks update-kubeconfig --region us-west-2 --name cancer-genomics-prod
   ```

2. **Install AWS Load Balancer Controller**:
   ```bash
   # Create IAM policy
   aws iam create-policy \
     --policy-name AWSLoadBalancerControllerIAMPolicy \
     --policy-document file://aws-lb-controller-policy.json

   # Create service account
   eksctl create iamserviceaccount \
     --cluster=cancer-genomics-prod \
     --namespace=kube-system \
     --name=aws-load-balancer-controller \
     --role-name AmazonEKSLoadBalancerControllerRole \
     --attach-policy-arn=arn:aws:iam::ACCOUNT_ID:policy/AWSLoadBalancerControllerIAMPolicy \
     --approve

   # Install controller
   helm repo add eks https://aws.github.io/eks-charts
   helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
     -n kube-system \
     --set clusterName=cancer-genomics-prod
   ```

3. **Install EBS CSI Driver**:
   ```bash
   # Create IAM policy
   aws iam create-policy \
     --policy-name AmazonEKS_EBS_CSI_Driver_Policy \
     --policy-document file://ebs-csi-policy.json

   # Create service account
   eksctl create iamserviceaccount \
     --cluster=cancer-genomics-prod \
     --namespace=kube-system \
     --name=ebs-csi-controller-sa \
     --role-name AmazonEKS_EBS_CSI_DriverRole \
     --attach-policy-arn=arn:aws:iam::ACCOUNT_ID:policy/AmazonEKS_EBS_CSI_Driver_Policy \
     --approve

   # Install driver
   helm repo add aws-ebs-csi-driver https://kubernetes-sigs.github.io/aws-ebs-csi-driver
   helm install aws-ebs-csi-driver aws-ebs-csi-driver/aws-ebs-csi-driver \
     --namespace kube-system \
     --set controller.serviceAccount.create=false \
     --set controller.serviceAccount.name=ebs-csi-controller-sa
   ```

4. **Deploy Application**:
   ```bash
   helm upgrade --install cancer-genomics-prod \
     ../../helm/cancer-genomics-analysis-suite \
     --namespace cancer-genomics-prod \
     --create-namespace \
     --set global.cloudProvider=aws \
     --set global.region=us-west-2 \
     --values ../../helm/cancer-genomics-analysis-suite/values-prod.yaml
   ```

### AWS-Specific Features

- **Network Load Balancer**: For high-performance load balancing
- **Application Load Balancer**: For advanced routing features
- **EBS CSI Driver**: For persistent volume management
- **EFS CSI Driver**: For shared file systems
- **CloudWatch Integration**: For logging and monitoring
- **X-Ray Tracing**: For distributed tracing

## GCP Deployment

### Prerequisites

1. **gcloud CLI Configuration**:
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **GKE Cluster**:
   ```bash
   # Create GKE cluster (if not exists)
   gcloud container clusters create cancer-genomics-prod \
     --region us-central1 \
     --num-nodes 3 \
     --machine-type e2-standard-2 \
     --enable-ip-alias \
     --enable-network-policy \
     --workload-pool=YOUR_PROJECT_ID.svc.id.goog
   ```

3. **Required APIs**:
   ```bash
   gcloud services enable \
     container.googleapis.com \
     compute.googleapis.com \
     storage.googleapis.com \
     sqladmin.googleapis.com \
     redis.googleapis.com \
     monitoring.googleapis.com \
     logging.googleapis.com
   ```

### Deployment

#### Automated Deployment

```bash
# Make script executable
chmod +x gcp-deploy.sh

# Deploy to GCP
./gcp-deploy.sh \
  --project-id your-gcp-project \
  --cluster-name cancer-genomics-prod \
  --region us-central1 \
  --environment production \
  --image-tag v1.0.0
```

#### Manual Deployment Steps

1. **Update kubeconfig**:
   ```bash
   gcloud container clusters get-credentials cancer-genomics-prod \
     --region us-central1 --project your-gcp-project
   ```

2. **Create Service Account**:
   ```bash
   # Create service account
   gcloud iam service-accounts create cancer-genomics-sa \
     --display-name="Cancer Genomics Service Account"

   # Grant permissions
   gcloud projects add-iam-policy-binding your-gcp-project \
     --member="serviceAccount:cancer-genomics-sa@your-gcp-project.iam.gserviceaccount.com" \
     --role="roles/storage.admin"

   gcloud projects add-iam-policy-binding your-gcp-project \
     --member="serviceAccount:cancer-genomics-sa@your-gcp-project.iam.gserviceaccount.com" \
     --role="roles/cloudsql.client"
   ```

3. **Create Workload Identity Binding**:
   ```bash
   gcloud iam service-accounts add-iam-policy-binding \
     --role roles/iam.workloadIdentityUser \
     --member "serviceAccount:your-gcp-project.svc.id.goog[cancer-genomics-prod/cancer-genomics-gcp-sa]" \
     cancer-genomics-sa@your-gcp-project.iam.gserviceaccount.com
   ```

4. **Deploy Application**:
   ```bash
   helm upgrade --install cancer-genomics-prod \
     ../../helm/cancer-genomics-analysis-suite \
     --namespace cancer-genomics-prod \
     --create-namespace \
     --set global.cloudProvider=gcp \
     --set global.region=us-central1 \
     --set global.gcp.projectId=your-gcp-project \
     --values ../../helm/cancer-genomics-analysis-suite/values-prod.yaml
   ```

### GCP-Specific Features

- **Cloud Load Balancing**: For global load balancing
- **Cloud SQL**: For managed PostgreSQL
- **Memorystore**: For managed Redis
- **Cloud Storage**: For object storage
- **Cloud Monitoring**: For metrics and alerting
- **Cloud Logging**: For centralized logging
- **Cloud Trace**: For distributed tracing

## Configuration Files

### AWS Load Balancer Controller Policy

The `aws-lb-controller-policy.json` file contains the IAM policy required for the AWS Load Balancer Controller to manage load balancers and target groups.

### EBS CSI Driver Policy

The `ebs-csi-policy.json` file contains the IAM policy required for the EBS CSI Driver to manage EBS volumes.

### GCS Lifecycle Configuration

The `gcs-lifecycle.json` file defines the lifecycle rules for GCS buckets, including automatic transitions between storage classes and deletion policies.

## Environment-Specific Configurations

### Development Environment

```bash
./aws-deploy.sh --environment development --cluster-name cancer-genomics-dev
```

### Staging Environment

```bash
./aws-deploy.sh --environment staging --cluster-name cancer-genomics-staging
```

### Production Environment

```bash
./aws-deploy.sh --environment production --cluster-name cancer-genomics-prod
```

## Troubleshooting

### Common Issues

#### 1. Permission Denied

```bash
# Check AWS credentials
aws sts get-caller-identity

# Check GCP authentication
gcloud auth list
```

#### 2. Cluster Not Found

```bash
# List AWS EKS clusters
aws eks list-clusters --region us-west-2

# List GCP GKE clusters
gcloud container clusters list --region us-central1
```

#### 3. Helm Installation Failed

```bash
# Check Helm repositories
helm repo list

# Update repositories
helm repo update
```

#### 4. Pod Startup Issues

```bash
# Check pod status
kubectl get pods -n cancer-genomics-prod

# Check pod logs
kubectl logs -n cancer-genomics-prod deployment/cancer-genomics-web

# Check events
kubectl get events -n cancer-genomics-prod --sort-by='.lastTimestamp'
```

### Logs and Debugging

#### Enable Debug Mode

```bash
# AWS deployment with debug
./aws-deploy.sh --environment production --debug

# GCP deployment with debug
./gcp-deploy.sh --project-id your-project --environment production --debug
```

#### Check Resource Status

```bash
# Check all resources
kubectl get all -n cancer-genomics-prod

# Check persistent volumes
kubectl get pv

# Check storage classes
kubectl get storageclass

# Check ingress
kubectl get ingress -n cancer-genomics-prod
```

## Security Considerations

### IAM Roles and Policies

- Use least privilege principle
- Regularly rotate access keys
- Enable MFA for administrative access
- Use IAM roles instead of access keys when possible

### Network Security

- Use VPC with private subnets
- Configure security groups properly
- Enable network policies
- Use TLS/SSL for all communications

### Secrets Management

- Use external secret management systems
- Encrypt secrets at rest and in transit
- Regularly rotate secrets
- Use RBAC for secret access

## Monitoring and Alerting

### CloudWatch (AWS)

- Set up CloudWatch alarms
- Configure log groups
- Enable X-Ray tracing
- Set up billing alerts

### Cloud Monitoring (GCP)

- Configure uptime checks
- Set up alerting policies
- Enable log-based metrics
- Configure notification channels

## Backup and Recovery

### Database Backups

- Enable automated backups
- Test restore procedures
- Store backups in multiple regions
- Document recovery procedures

### Application Backups

- Backup Helm releases
- Backup configurations
- Backup persistent volumes
- Test disaster recovery procedures

## Support

For additional support:

- **GitHub Issues**: [Create an issue](https://github.com/your-org/cancer-genomics-analysis-suite/issues)
- **Documentation**: [Read the docs](https://docs.cancer-genomics.com)
- **Community**: [Join our Slack](https://cancer-genomics.slack.com)

## License

This project is licensed under the MIT License - see the [LICENSE](../../LICENSE) file for details.
