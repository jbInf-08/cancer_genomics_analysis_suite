#!/bin/bash

# Cancer Genomics Analysis Suite - Security-Enhanced Deployment Script
# This script deploys the application with comprehensive security features enabled

set -e

# Configuration
NAMESPACE="cancer-genomics-prod"
RELEASE_NAME="cancer-genomics"
CHART_PATH="./helm/cancer-genomics-analysis-suite"
VALUES_FILE="values-production.yaml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check if helm is installed
    if ! command -v helm &> /dev/null; then
        log_error "helm is not installed or not in PATH"
        exit 1
    fi
    
    # Check if cert-manager is installed
    if ! kubectl get crd certificates.cert-manager.io &> /dev/null; then
        log_error "cert-manager is not installed. Please install cert-manager first."
        exit 1
    fi
    
    # Check if nginx-ingress is installed
    if ! kubectl get pods -n ingress-nginx &> /dev/null; then
        log_warning "nginx-ingress controller not found. Please ensure it's installed."
    fi
    
    log_success "Prerequisites check completed"
}

# Create namespace
create_namespace() {
    log_info "Creating namespace: $NAMESPACE"
    
    if kubectl get namespace $NAMESPACE &> /dev/null; then
        log_info "Namespace $NAMESPACE already exists"
    else
        kubectl create namespace $NAMESPACE
        log_success "Namespace $NAMESPACE created"
    fi
}

# Create secrets
create_secrets() {
    log_info "Creating secrets..."
    
    # Create registry secret if needed
    if [ -n "$DOCKER_USERNAME" ] && [ -n "$DOCKER_PASSWORD" ]; then
        kubectl create secret docker-registry registry-secret \
            --docker-server=$DOCKER_REGISTRY \
            --docker-username=$DOCKER_USERNAME \
            --docker-password=$DOCKER_PASSWORD \
            --namespace=$NAMESPACE \
            --dry-run=client -o yaml | kubectl apply -f -
        log_success "Registry secret created"
    fi
    
    # Create basic auth secrets for API and Admin
    kubectl create secret generic api-basic-auth \
        --from-literal=auth=$(echo -n "$API_USERNAME:$API_PASSWORD" | base64) \
        --namespace=$NAMESPACE \
        --dry-run=client -o yaml | kubectl apply -f -
    
    kubectl create secret generic admin-basic-auth \
        --from-literal=auth=$(echo -n "$ADMIN_USERNAME:$ADMIN_PASSWORD" | base64) \
        --namespace=$NAMESPACE \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_success "Basic auth secrets created"
}

# Deploy with security features
deploy_with_security() {
    log_info "Deploying Cancer Genomics Analysis Suite with security features..."
    
    # Check if release exists
    if helm list -n $NAMESPACE | grep -q $RELEASE_NAME; then
        log_info "Upgrading existing release: $RELEASE_NAME"
        helm upgrade $RELEASE_NAME $CHART_PATH \
            -f $VALUES_FILE \
            --namespace $NAMESPACE \
            --set security.networkPolicy.enabled=true \
            --set security.mtls.enabled=true \
            --set security.secrets.rotation.enabled=true \
            --set security.secrets.audit.enabled=true \
            --set security.secrets.validation.enabled=true \
            --set security.waf.enabled=true \
            --set security.monitoring.enabled=true \
            --set security.compliance.enabled=true \
            --set security.incidentResponse.enabled=true \
            --set security.certificateMonitoring.enabled=true \
            --set ingress.enabled=true \
            --set ingress.api.enabled=true \
            --set ingress.admin.enabled=true \
            --wait \
            --timeout=10m
    else
        log_info "Installing new release: $RELEASE_NAME"
        helm install $RELEASE_NAME $CHART_PATH \
            -f $VALUES_FILE \
            --namespace $NAMESPACE \
            --create-namespace \
            --set security.networkPolicy.enabled=true \
            --set security.mtls.enabled=true \
            --set security.secrets.rotation.enabled=true \
            --set security.secrets.audit.enabled=true \
            --set security.secrets.validation.enabled=true \
            --set security.waf.enabled=true \
            --set security.monitoring.enabled=true \
            --set security.compliance.enabled=true \
            --set security.incidentResponse.enabled=true \
            --set security.certificateMonitoring.enabled=true \
            --set ingress.enabled=true \
            --set ingress.api.enabled=true \
            --set ingress.admin.enabled=true \
            --wait \
            --timeout=10m
    fi
    
    log_success "Deployment completed"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check pods
    log_info "Checking pod status..."
    kubectl get pods -n $NAMESPACE
    
    # Check services
    log_info "Checking services..."
    kubectl get services -n $NAMESPACE
    
    # Check ingress
    log_info "Checking ingress..."
    kubectl get ingress -n $NAMESPACE
    
    # Check network policies
    log_info "Checking network policies..."
    kubectl get networkpolicies -n $NAMESPACE
    
    # Check certificates
    log_info "Checking certificates..."
    kubectl get certificates -n $NAMESPACE
    
    # Check secrets
    log_info "Checking secrets..."
    kubectl get secrets -n $NAMESPACE
    
    log_success "Deployment verification completed"
}

# Display security status
display_security_status() {
    log_info "Security Features Status:"
    
    echo "✅ Network Policies: Enabled"
    echo "✅ mTLS: Enabled"
    echo "✅ Secret Rotation: Enabled"
    echo "✅ Secret Audit: Enabled"
    echo "✅ Secret Validation: Enabled"
    echo "✅ WAF: Enabled"
    echo "✅ Security Monitoring: Enabled"
    echo "✅ Compliance Monitoring: Enabled"
    echo "✅ Incident Response: Enabled"
    echo "✅ Certificate Monitoring: Enabled"
    echo "✅ Advanced Ingress: Enabled"
    echo "✅ API Security: Enabled"
    echo "✅ Admin Security: Enabled"
}

# Main deployment function
main() {
    log_info "Starting Cancer Genomics Analysis Suite deployment with security enhancements..."
    
    # Check if values file exists
    if [ ! -f "$VALUES_FILE" ]; then
        log_error "Values file $VALUES_FILE not found"
        exit 1
    fi
    
    # Check prerequisites
    check_prerequisites
    
    # Create namespace
    create_namespace
    
    # Create secrets
    create_secrets
    
    # Deploy with security features
    deploy_with_security
    
    # Verify deployment
    verify_deployment
    
    # Display security status
    display_security_status
    
    log_success "Deployment completed successfully!"
    log_info "Access your application at: https://cancer-genomics.yourdomain.com"
    log_info "API endpoint: https://api.cancer-genomics.yourdomain.com"
    log_info "Admin interface: https://admin.cancer-genomics.yourdomain.com"
}

# Help function
show_help() {
    echo "Cancer Genomics Analysis Suite - Security-Enhanced Deployment Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -n, --namespace NAME    Kubernetes namespace (default: cancer-genomics-prod)"
    echo "  -r, --release NAME      Helm release name (default: cancer-genomics)"
    echo "  -f, --values FILE       Values file (default: values-production.yaml)"
    echo ""
    echo "Environment Variables:"
    echo "  DOCKER_USERNAME         Docker registry username"
    echo "  DOCKER_PASSWORD         Docker registry password"
    echo "  DOCKER_REGISTRY         Docker registry URL"
    echo "  API_USERNAME            API basic auth username"
    echo "  API_PASSWORD            API basic auth password"
    echo "  ADMIN_USERNAME          Admin basic auth username"
    echo "  ADMIN_PASSWORD          Admin basic auth password"
    echo ""
    echo "Example:"
    echo "  $0 --namespace my-namespace --release my-release"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -r|--release)
            RELEASE_NAME="$2"
            shift 2
            ;;
        -f|--values)
            VALUES_FILE="$2"
            shift 2
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Run main function
main
