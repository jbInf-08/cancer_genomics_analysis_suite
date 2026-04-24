#!/bin/bash

# GCP Deployment Script for Cancer Genomics Analysis Suite
# This script deploys the application to GCP GKE with all necessary configurations

set -e

# Configuration
CLUSTER_NAME=${CLUSTER_NAME:-"cancer-genomics-prod"}
PROJECT_ID=${PROJECT_ID:-"your-project-id"}
REGION=${GCP_REGION:-"us-central1"}
ZONE=${GCP_ZONE:-"us-central1-a"}
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
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is not installed. Please install it first."
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
    
    # Check if gcloud is authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log_error "gcloud is not authenticated. Please run 'gcloud auth login' first."
        exit 1
    fi
    
    # Set project
    gcloud config set project $PROJECT_ID
    
    log_info "Prerequisites check passed!"
}

# Update kubeconfig for GKE cluster
update_kubeconfig() {
    log_info "Updating kubeconfig for GKE cluster: $CLUSTER_NAME"
    gcloud container clusters get-credentials $CLUSTER_NAME --region $REGION --project $PROJECT_ID
}

# Enable required APIs
enable_apis() {
    log_info "Enabling required GCP APIs..."
    
    gcloud services enable \
        container.googleapis.com \
        compute.googleapis.com \
        storage.googleapis.com \
        sqladmin.googleapis.com \
        redis.googleapis.com \
        monitoring.googleapis.com \
        logging.googleapis.com \
        cloudtrace.googleapis.com \
        cloudprofiler.googleapis.com \
        --project $PROJECT_ID
}

# Install GKE Add-ons
install_gke_addons() {
    log_info "Installing GKE add-ons..."
    
    # Enable Workload Identity
    gcloud container clusters update $CLUSTER_NAME \
        --region $REGION \
        --workload-pool=$PROJECT_ID.svc.id.goog \
        --project $PROJECT_ID
    
    # Enable HTTP Load Balancing
    gcloud container clusters update $CLUSTER_NAME \
        --region $REGION \
        --enable-http-load-balancing \
        --project $PROJECT_ID
    
    # Enable Network Policy
    gcloud container clusters update $CLUSTER_NAME \
        --region $REGION \
        --enable-network-policy \
        --project $PROJECT_ID
}

# Create GCS bucket for application data
create_gcs_bucket() {
    log_info "Creating GCS bucket for application data..."
    
    BUCKET_NAME="cancer-genomics-${PROJECT_ID}-data"
    
    if ! gsutil ls -b gs://$BUCKET_NAME &> /dev/null; then
        gsutil mb -l $REGION gs://$BUCKET_NAME
        gsutil versioning set on gs://$BUCKET_NAME
        gsutil lifecycle set scripts/deploy/gcs-lifecycle.json gs://$BUCKET_NAME
        log_info "GCS bucket created: $BUCKET_NAME"
    else
        log_info "GCS bucket already exists: $BUCKET_NAME"
    fi
}

# Create Cloud SQL instance
create_cloud_sql() {
    log_info "Creating Cloud SQL instance..."
    
    INSTANCE_NAME="cancer-genomics-${ENVIRONMENT}-db"
    
    if ! gcloud sql instances describe $INSTANCE_NAME --project $PROJECT_ID &> /dev/null; then
        gcloud sql instances create $INSTANCE_NAME \
            --database-version=POSTGRES_15 \
            --tier=db-standard-2 \
            --region=$REGION \
            --storage-type=SSD \
            --storage-size=20GB \
            --storage-auto-increase \
            --backup \
            --enable-ip-alias \
            --network=default \
            --no-assign-ip \
            --project $PROJECT_ID
        
        # Create database
        gcloud sql databases create genomics_db --instance=$INSTANCE_NAME --project $PROJECT_ID
        
        # Create user
        gcloud sql users create cancer_genomics_user \
            --instance=$INSTANCE_NAME \
            --password=$(openssl rand -base64 32) \
            --project $PROJECT_ID
        
        log_info "Cloud SQL instance created: $INSTANCE_NAME"
    else
        log_info "Cloud SQL instance already exists: $INSTANCE_NAME"
    fi
}

# Create Memorystore Redis instance
create_memorystore() {
    log_info "Creating Memorystore Redis instance..."
    
    INSTANCE_NAME="cancer-genomics-${ENVIRONMENT}-cache"
    
    if ! gcloud redis instances describe $INSTANCE_NAME --region $REGION --project $PROJECT_ID &> /dev/null; then
        gcloud redis instances create $INSTANCE_NAME \
            --size=1 \
            --region=$REGION \
            --redis-version=redis_7_0 \
            --network=default \
            --project $PROJECT_ID
        
        log_info "Memorystore Redis instance created: $INSTANCE_NAME"
    else
        log_info "Memorystore Redis instance already exists: $INSTANCE_NAME"
    fi
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
        --set controller.service.annotations."cloud\.google\.com/load-balancer-type"="External" || log_warn "nginx-ingress may already be installed"
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

# Create Workload Identity binding
create_workload_identity() {
    log_info "Creating Workload Identity binding..."
    
    # Create service account
    gcloud iam service-accounts create cancer-genomics-sa \
        --display-name="Cancer Genomics Service Account" \
        --description="Service account for Cancer Genomics Analysis Suite" \
        --project $PROJECT_ID || log_warn "Service account may already exist"
    
    # Grant necessary permissions
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:cancer-genomics-sa@$PROJECT_ID.iam.gserviceaccount.com" \
        --role="roles/storage.admin"
    
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:cancer-genomics-sa@$PROJECT_ID.iam.gserviceaccount.com" \
        --role="roles/cloudsql.client"
    
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:cancer-genomics-sa@$PROJECT_ID.iam.gserviceaccount.com" \
        --role="roles/redis.editor"
    
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:cancer-genomics-sa@$PROJECT_ID.iam.gserviceaccount.com" \
        --role="roles/monitoring.metricWriter"
    
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:cancer-genomics-sa@$PROJECT_ID.iam.gserviceaccount.com" \
        --role="roles/logging.logWriter"
    
    # Create Workload Identity binding
    gcloud iam service-accounts add-iam-policy-binding \
        --role roles/iam.workloadIdentityUser \
        --member "serviceAccount:$PROJECT_ID.svc.id.goog[$NAMESPACE/cancer-genomics-gcp-sa]" \
        cancer-genomics-sa@$PROJECT_ID.iam.gserviceaccount.com \
        --project $PROJECT_ID
}

# Deploy the application
deploy_application() {
    log_info "Deploying Cancer Genomics Analysis Suite..."
    
    # Create namespace
    kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    
    # Deploy with Helm
    helm upgrade --install $HELM_RELEASE_NAME ./helm/cancer-genomics-analysis-suite \
        --namespace $NAMESPACE \
        --set global.cloudProvider=gcp \
        --set global.region=$REGION \
        --set global.gcp.gkeClusterName=$CLUSTER_NAME \
        --set global.gcp.projectId=$PROJECT_ID \
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
    
    echo -e "\n=== Load Balancer IP ==="
    kubectl get service ingress-nginx-controller -n ingress-nginx -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
}

# Main deployment function
main() {
    log_info "Starting GCP deployment for Cancer Genomics Analysis Suite"
    log_info "Project: $PROJECT_ID"
    log_info "Cluster: $CLUSTER_NAME"
    log_info "Region: $REGION"
    log_info "Namespace: $NAMESPACE"
    log_info "Environment: $ENVIRONMENT"
    log_info "Image Tag: $IMAGE_TAG"
    
    check_prerequisites
    enable_apis
    update_kubeconfig
    install_gke_addons
    create_gcs_bucket
    create_cloud_sql
    create_memorystore
    create_workload_identity
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
        --project-id)
            PROJECT_ID="$2"
            shift 2
            ;;
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
            echo "  --project-id      GCP project ID (required)"
            echo "  --cluster-name    GKE cluster name (default: cancer-genomics-prod)"
            echo "  --region          GCP region (default: us-central1)"
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

# Validate required parameters
if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" = "your-project-id" ]; then
    log_error "Project ID is required. Please provide --project-id parameter."
    exit 1
fi

# Run main function
main
