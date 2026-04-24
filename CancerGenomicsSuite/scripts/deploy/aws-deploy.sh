#!/bin/bash

# AWS Deployment Script for Cancer Genomics Analysis Suite
# This script deploys the application to AWS EKS with all necessary configurations

set -e

# Configuration
CLUSTER_NAME=${CLUSTER_NAME:-"cancer-genomics-prod"}
REGION=${AWS_REGION:-"us-west-2"}
NAMESPACE=${NAMESPACE:-"cancer-genomics-prod"}
ENVIRONMENT=${ENVIRONMENT:-"production"}
IMAGE_TAG=${IMAGE_TAG:-"latest"}
HELM_RELEASE_NAME=${HELM_RELEASE_NAME:-"cancer-genomics-prod"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed. Please install it first."
        exit 1
    fi
    
    # Check if helm is installed
    if ! command -v helm &> /dev/null; then
        log_error "Helm is not installed. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    log_info "Prerequisites check passed!"
}

# Update kubeconfig for EKS cluster
update_kubeconfig() {
    log_info "Updating kubeconfig for EKS cluster: $CLUSTER_NAME"
    aws eks update-kubeconfig --region $REGION --name $CLUSTER_NAME
}

# Install AWS Load Balancer Controller
install_aws_load_balancer_controller() {
    log_info "Installing AWS Load Balancer Controller..."
    
    # Create IAM policy for AWS Load Balancer Controller
    aws iam create-policy \
        --policy-name AWSLoadBalancerControllerIAMPolicy \
        --policy-document file://scripts/deploy/aws-lb-controller-policy.json \
        --region $REGION || log_warn "Policy may already exist"
    
    # Create service account
    eksctl create iamserviceaccount \
        --cluster=$CLUSTER_NAME \
        --namespace=kube-system \
        --name=aws-load-balancer-controller \
        --role-name AmazonEKSLoadBalancerControllerRole \
        --attach-policy-arn=arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):policy/AWSLoadBalancerControllerIAMPolicy \
        --approve \
        --region $REGION || log_warn "Service account may already exist"
    
    # Install AWS Load Balancer Controller
    helm repo add eks https://aws.github.io/eks-charts
    helm repo update
    
    helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
        -n kube-system \
        --set clusterName=$CLUSTER_NAME \
        --set serviceAccount.create=false \
        --set serviceAccount.name=aws-load-balancer-controller \
        --set region=$REGION \
        --set vpcId=$(aws eks describe-cluster --name $CLUSTER_NAME --region $REGION --query "cluster.resourcesVpcConfig.vpcId" --output text) || log_warn "AWS Load Balancer Controller may already be installed"
}

# Install EBS CSI Driver
install_ebs_csi_driver() {
    log_info "Installing EBS CSI Driver..."
    
    # Create IAM policy for EBS CSI Driver
    aws iam create-policy \
        --policy-name AmazonEKS_EBS_CSI_Driver_Policy \
        --policy-document file://scripts/deploy/ebs-csi-policy.json \
        --region $REGION || log_warn "Policy may already exist"
    
    # Create service account
    eksctl create iamserviceaccount \
        --cluster=$CLUSTER_NAME \
        --namespace=kube-system \
        --name=ebs-csi-controller-sa \
        --role-name AmazonEKS_EBS_CSI_DriverRole \
        --attach-policy-arn=arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):policy/AmazonEKS_EBS_CSI_Driver_Policy \
        --approve \
        --region $REGION || log_warn "Service account may already exist"
    
    # Install EBS CSI Driver
    helm repo add aws-ebs-csi-driver https://kubernetes-sigs.github.io/aws-ebs-csi-driver
    helm repo update
    
    helm install aws-ebs-csi-driver aws-ebs-csi-driver/aws-ebs-csi-driver \
        --namespace kube-system \
        --set controller.serviceAccount.create=false \
        --set controller.serviceAccount.name=ebs-csi-controller-sa || log_warn "EBS CSI Driver may already be installed"
}

# Install EFS CSI Driver
install_efs_csi_driver() {
    log_info "Installing EFS CSI Driver..."
    
    # Create EFS file system
    EFS_ID=$(aws efs describe-file-systems --query "FileSystems[?CreationToken=='cancer-genomics-efs'].FileSystemId" --output text --region $REGION)
    
    if [ -z "$EFS_ID" ]; then
        log_info "Creating EFS file system..."
        EFS_ID=$(aws efs create-file-system \
            --creation-token cancer-genomics-efs \
            --performance-mode generalPurpose \
            --throughput-mode provisioned \
            --provisioned-throughput-in-mibps 100 \
            --tags Key=Name,Value=cancer-genomics-efs \
            --region $REGION \
            --query 'FileSystemId' --output text)
        
        log_info "EFS file system created: $EFS_ID"
        
        # Wait for EFS to be available
        aws efs wait file-system-available --file-system-id $EFS_ID --region $REGION
    else
        log_info "Using existing EFS file system: $EFS_ID"
    fi
    
    # Install EFS CSI Driver
    kubectl apply -k "github.com/kubernetes-sigs/aws-efs-csi-driver/deploy/kubernetes/overlays/stable/?ref=release-1.5"
    
    # Create EFS StorageClass
    cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: $EFS_ID
  directoryPerms: "0755"
  gidRangeStart: "1000"
  gidRangeEnd: "2000"
reclaimPolicy: Retain
allowVolumeExpansion: false
volumeBindingMode: Immediate
EOF
}

# Install cert-manager
install_cert_manager() {
    log_info "Installing cert-manager..."
    
    helm repo add jetstack https://charts.jetstack.io
    helm repo update
    
    helm install cert-manager jetstack/cert-manager \
        --namespace cert-manager \
        --create-namespace \
        --version v1.13.0 \
        --set installCRDs=true || log_warn "cert-manager may already be installed"
    
    # Wait for cert-manager to be ready
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=cert-manager -n cert-manager --timeout=300s
}

# Install nginx-ingress
install_nginx_ingress() {
    log_info "Installing nginx-ingress..."
    
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    helm repo update
    
    helm install ingress-nginx ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        --set controller.service.type=LoadBalancer \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-type"="nlb" \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-cross-zone-load-balancing-enabled"="true" || log_warn "nginx-ingress may already be installed"
}

# Install Argo Workflows
install_argo_workflows() {
    log_info "Installing Argo Workflows..."
    
    # Create namespace
    kubectl create namespace argo --dry-run=client -o yaml | kubectl apply -f -
    
    # Install Argo Workflows
    kubectl apply -n argo -f https://github.com/argoproj/argo-workflows/releases/download/v3.4.11/install.yaml
    
    # Wait for Argo Workflows to be ready
    kubectl wait --for=condition=ready pod -l app=argo-server -n argo --timeout=300s
}

# Install Prometheus and Grafana
install_monitoring() {
    log_info "Installing Prometheus and Grafana..."
    
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    
    # Install Prometheus
    helm install prometheus prometheus-community/kube-prometheus-stack \
        --namespace monitoring \
        --create-namespace \
        --set grafana.adminPassword=admin \
        --set prometheus.prometheusSpec.retention=30d || log_warn "Prometheus may already be installed"
    
    # Wait for monitoring to be ready
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=prometheus -n monitoring --timeout=300s
}

# Deploy the application
deploy_application() {
    log_info "Deploying Cancer Genomics Analysis Suite..."
    
    # Create namespace
    kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    
    # Deploy with Helm
    helm upgrade --install $HELM_RELEASE_NAME ./helm/cancer-genomics-analysis-suite \
        --namespace $NAMESPACE \
        --set global.cloudProvider=aws \
        --set global.region=$REGION \
        --set global.aws.eksClusterName=$CLUSTER_NAME \
        --set image.tag=$IMAGE_TAG \
        --values ./helm/cancer-genomics-analysis-suite/values-$ENVIRONMENT.yaml \
        --wait \
        --timeout=10m
    
    log_info "Application deployed successfully!"
}

# Get application status
get_status() {
    log_info "Getting application status..."
    
    echo "=== Pods ==="
    kubectl get pods -n $NAMESPACE
    
    echo -e "\n=== Services ==="
    kubectl get services -n $NAMESPACE
    
    echo -e "\n=== Ingress ==="
    kubectl get ingress -n $NAMESPACE
    
    echo -e "\n=== Helm Release ==="
    helm list -n $NAMESPACE
}

# Main deployment function
main() {
    log_info "Starting AWS deployment for Cancer Genomics Analysis Suite"
    log_info "Cluster: $CLUSTER_NAME"
    log_info "Region: $REGION"
    log_info "Namespace: $NAMESPACE"
    log_info "Environment: $ENVIRONMENT"
    log_info "Image Tag: $IMAGE_TAG"
    
    check_prerequisites
    update_kubeconfig
    install_aws_load_balancer_controller
    install_ebs_csi_driver
    install_efs_csi_driver
    install_cert_manager
    install_nginx_ingress
    install_argo_workflows
    install_monitoring
    deploy_application
    get_status
    
    log_info "Deployment completed successfully!"
    log_info "You can access the application at: https://cancer-genomics.yourdomain.com"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --cluster-name)
            CLUSTER_NAME="$2"
            shift 2
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --image-tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --cluster-name    EKS cluster name (default: cancer-genomics-prod)"
            echo "  --region          AWS region (default: us-west-2)"
            echo "  --namespace       Kubernetes namespace (default: cancer-genomics-prod)"
            echo "  --environment     Environment (default: production)"
            echo "  --image-tag       Docker image tag (default: latest)"
            echo "  --help            Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main
