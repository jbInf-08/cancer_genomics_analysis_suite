#!/bin/bash
# Docker Deployment Script for Cancer Genomics Analysis Suite
# This script handles complete deployment workflow: build, tag, push, and deploy

set -e

# Configuration
IMAGE_NAME="cancer-genomics-analysis-suite"
DEFAULT_REGISTRY="docker.io"
DEFAULT_USERNAME="${DOCKER_HUB_USERNAME:-your-username}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
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

show_help() {
    cat << EOF
Docker Deployment Script for Cancer Genomics Analysis Suite

Usage: $0 [OPTIONS]

OPTIONS:
    -t, --tag TAG           Tag for the Docker image (default: latest)
    -r, --registry REGISTRY Docker registry (default: docker.io)
    -u, --username USERNAME Docker Hub username (default: your-username)
    -e, --environment ENV   Deployment environment (dev, staging, prod)
    -b, --build             Build image before deployment
    -p, --push              Push image to registry
    -d, --deploy            Deploy to Kubernetes
    -c, --cleanup           Clean up old images after deployment
    -m, --multiarch         Build multi-architecture image
    -v, --verbose           Verbose output
    -h, --help              Show this help message

DEPLOYMENT STAGES:
    1. Build    - Build Docker image
    2. Tag      - Tag image for registry
    3. Push     - Push image to registry
    4. Deploy   - Deploy to Kubernetes
    5. Cleanup  - Clean up old images

EXAMPLES:
    $0 -b -p -d -e prod -t v1.0.0    # Full deployment to production
    $0 -b -e dev -t dev              # Build and deploy to development
    $0 -p -d -e staging -t latest    # Push and deploy to staging
    $0 -d -e prod -t v1.0.0          # Deploy existing image to production

ENVIRONMENT VARIABLES:
    DOCKER_HUB_USERNAME     Docker Hub username
    DOCKER_HUB_TOKEN        Docker Hub access token
    KUBECONFIG              Kubernetes configuration file
    NAMESPACE               Kubernetes namespace (default: cancer-genomics)

EOF
}

# Default values
TAG="latest"
REGISTRY="$DEFAULT_REGISTRY"
USERNAME="$DEFAULT_USERNAME"
ENVIRONMENT="dev"
BUILD=false
PUSH=false
DEPLOY=false
CLEANUP=false
MULTIARCH=false
VERBOSE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -u|--username)
            USERNAME="$2"
            shift 2
            ;;
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -b|--build)
            BUILD=true
            shift
            ;;
        -p|--push)
            PUSH=true
            shift
            ;;
        -d|--deploy)
            DEPLOY=true
            shift
            ;;
        -c|--cleanup)
            CLEANUP=true
            shift
            ;;
        -m|--multiarch)
            MULTIARCH=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Set repository name
REPOSITORY="${USERNAME}/${IMAGE_NAME}"
FULL_IMAGE_NAME="${REGISTRY}/${REPOSITORY}:${TAG}"

# Set Kubernetes namespace based on environment
case "$ENVIRONMENT" in
    "dev"|"development")
        NAMESPACE="cancer-genomics-dev"
        ;;
    "staging")
        NAMESPACE="cancer-genomics-staging"
        ;;
    "prod"|"production")
        NAMESPACE="cancer-genomics"
        ;;
    *)
        NAMESPACE="cancer-genomics-${ENVIRONMENT}"
        ;;
esac

log_info "Deployment Configuration:"
log_info "  Environment: ${ENVIRONMENT}"
log_info "  Namespace: ${NAMESPACE}"
log_info "  Registry: ${REGISTRY}"
log_info "  Repository: ${REPOSITORY}"
log_info "  Tag: ${TAG}"
log_info "  Full image: ${FULL_IMAGE_NAME}"
log_info "  Build: ${BUILD}"
log_info "  Push: ${PUSH}"
log_info "  Deploy: ${DEPLOY}"
log_info "  Cleanup: ${CLEANUP}"

# Build stage
build_image() {
    log_info "Building Docker image..."
    
    local build_script="scripts/docker/build.sh"
    local build_cmd="${build_script} -t ${TAG} -r ${REGISTRY} -u ${USERNAME}"
    
    if [[ "$MULTIARCH" == "true" ]]; then
        build_cmd="${build_cmd} -m"
    fi
    
    if [[ "$VERBOSE" == "true" ]]; then
        build_cmd="${build_cmd} -v"
    fi
    
    if [[ "$PUSH" == "true" ]]; then
        build_cmd="${build_cmd} -p"
    fi
    
    if eval "${build_cmd}"; then
        log_success "Image built successfully"
        return 0
    else
        log_error "Image build failed"
        return 1
    fi
}

# Push stage
push_image() {
    log_info "Pushing Docker image..."
    
    local push_script="scripts/docker/push.sh"
    local push_cmd="${push_script} -t ${TAG} -r ${REGISTRY} -u ${USERNAME}"
    
    if [[ "$VERBOSE" == "true" ]]; then
        push_cmd="${push_cmd} -v"
    fi
    
    if eval "${push_cmd}"; then
        log_success "Image pushed successfully"
        return 0
    else
        log_error "Image push failed"
        return 1
    fi
}

# Deploy stage
deploy_to_kubernetes() {
    log_info "Deploying to Kubernetes..."
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        return 1
    fi
    
    # Check if kubeconfig is set
    if [[ -z "$KUBECONFIG" && ! -f "$HOME/.kube/config" ]]; then
        log_error "Kubernetes configuration not found. Please set KUBECONFIG or ensure ~/.kube/config exists"
        return 1
    fi
    
    # Check if namespace exists
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_warning "Namespace ${NAMESPACE} does not exist. Creating it..."
        kubectl create namespace "$NAMESPACE"
    fi
    
    # Update image tag in kustomization
    local kustomization_file="k8s/kustomization.yaml"
    if [[ -f "$kustomization_file" ]]; then
        log_info "Updating image tag in kustomization..."
        sed -i.bak "s/newTag: .*/newTag: ${TAG}/" "$kustomization_file"
    fi
    
    # Deploy using kustomize
    log_info "Deploying with kustomize..."
    if kubectl apply -k k8s/ -n "$NAMESPACE"; then
        log_success "Kubernetes deployment applied successfully"
    else
        log_error "Kubernetes deployment failed"
        return 1
    fi
    
    # Wait for rollout
    log_info "Waiting for deployment rollout..."
    if kubectl rollout status deployment/cancer-genomics-web -n "$NAMESPACE" --timeout=600s; then
        log_success "Deployment rollout completed successfully"
    else
        log_error "Deployment rollout failed or timed out"
        return 1
    fi
    
    # Show deployment status
    log_info "Deployment status:"
    kubectl get pods -n "$NAMESPACE" -l app=cancer-genomics-web
    
    # Show service information
    log_info "Service information:"
    kubectl get services -n "$NAMESPACE"
    
    return 0
}

# Cleanup stage
cleanup_old_images() {
    log_info "Cleaning up old images..."
    
    # Remove old local images (keep last 3 versions)
    log_info "Removing old local images..."
    docker images "${IMAGE_NAME}" --format "{{.Tag}}" | grep -v "$TAG" | head -n -3 | xargs -r -I {} docker rmi "${IMAGE_NAME}:{}" || true
    
    # Remove dangling images
    log_info "Removing dangling images..."
    docker image prune -f
    
    # Remove unused volumes (optional)
    if [[ "$ENVIRONMENT" == "dev" ]]; then
        log_info "Removing unused volumes..."
        docker volume prune -f
    fi
    
    log_success "Cleanup completed"
}

# Health check
health_check() {
    log_info "Performing health check..."
    
    # Get service URL
    local service_url
    if [[ "$ENVIRONMENT" == "prod" || "$ENVIRONMENT" == "production" ]]; then
        service_url=$(kubectl get service nginx-service -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    else
        service_url="localhost"
    fi
    
    if [[ -n "$service_url" ]]; then
        log_info "Checking health endpoint: http://${service_url}/health"
        
        # Wait for service to be ready
        local max_attempts=30
        local attempt=1
        
        while [[ $attempt -le $max_attempts ]]; do
            if curl -f -s "http://${service_url}/health" >/dev/null 2>&1; then
                log_success "Health check passed"
                return 0
            fi
            
            log_info "Health check attempt ${attempt}/${max_attempts} failed, retrying in 10 seconds..."
            sleep 10
            ((attempt++))
        done
        
        log_error "Health check failed after ${max_attempts} attempts"
        return 1
    else
        log_warning "Could not determine service URL for health check"
        return 0
    fi
}

# Main execution
main() {
    local start_time=$(date +%s)
    
    log_info "Starting deployment process..."
    
    # Build stage
    if [[ "$BUILD" == "true" ]]; then
        if ! build_image; then
            log_error "Build stage failed"
            exit 1
        fi
    fi
    
    # Push stage
    if [[ "$PUSH" == "true" ]]; then
        if ! push_image; then
            log_error "Push stage failed"
            exit 1
        fi
    fi
    
    # Deploy stage
    if [[ "$DEPLOY" == "true" ]]; then
        if ! deploy_to_kubernetes; then
            log_error "Deploy stage failed"
            exit 1
        fi
        
        # Health check after deployment
        if ! health_check; then
            log_error "Health check failed"
            exit 1
        fi
    fi
    
    # Cleanup stage
    if [[ "$CLEANUP" == "true" ]]; then
        cleanup_old_images
    fi
    
    # Summary
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_success "Deployment completed successfully in ${duration} seconds"
    log_info "Deployed image: ${FULL_IMAGE_NAME}"
    log_info "Environment: ${ENVIRONMENT}"
    log_info "Namespace: ${NAMESPACE}"
}

# Run main function
main
