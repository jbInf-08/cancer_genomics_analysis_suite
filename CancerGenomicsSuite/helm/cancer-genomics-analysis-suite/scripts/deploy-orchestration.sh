#!/bin/bash

# Helm Deployment Orchestration Script for Cancer Genomics Analysis Suite
# This script provides comprehensive deployment orchestration with Vault + SealedSecrets integration

set -euo pipefail

# Configuration
HELM_CHART_PATH="${HELM_CHART_PATH:-./cancer-genomics-analysis-suite}"
RELEASE_NAME="${RELEASE_NAME:-cancer-genomics}"
NAMESPACE="${NAMESPACE:-cancer-genomics}"
ENVIRONMENT="${ENVIRONMENT:-staging}"
SECRETS_STRATEGY="${SECRETS_STRATEGY:-vault}"
DRY_RUN="${DRY_RUN:-false}"
FORCE_UPGRADE="${FORCE_UPGRADE:-false}"
BACKUP_BEFORE_DEPLOY="${BACKUP_BEFORE_DEPLOY:-true}"
VALIDATE_AFTER_DEPLOY="${VALIDATE_AFTER_DEPLOY:-true}"
ROLLBACK_ON_FAILURE="${ROLLBACK_ON_FAILURE:-true}"

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
    
    if ! command -v helm &> /dev/null; then
        log_error "Helm is not installed"
        exit 1
    fi
    
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Kubernetes cluster is not accessible"
        exit 1
    fi
    
    if [ ! -d "$HELM_CHART_PATH" ]; then
        log_error "Helm chart path not found: $HELM_CHART_PATH"
        exit 1
    fi
    
    log_success "All prerequisites are met"
}

# Create namespace
create_namespace() {
    log_info "Creating namespace: $NAMESPACE"
    
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
    
    log_success "Namespace $NAMESPACE created/verified"
}

# Setup secrets management
setup_secrets_management() {
    log_info "Setting up secrets management with strategy: $SECRETS_STRATEGY"
    
    case "$SECRETS_STRATEGY" in
        "vault")
            setup_vault
            ;;
        "sealed-secrets")
            setup_sealed_secrets
            ;;
        "cloud-manager")
            setup_cloud_secrets
            ;;
        "hybrid")
            setup_vault
            setup_sealed_secrets
            setup_cloud_secrets
            ;;
        *)
            log_error "Unsupported secrets strategy: $SECRETS_STRATEGY"
            exit 1
            ;;
    esac
    
    log_success "Secrets management setup completed"
}

# Setup Vault
setup_vault() {
    log_info "Setting up Vault..."
    
    if [ -f "$HELM_CHART_PATH/scripts/vault-provisioning.sh" ]; then
        chmod +x "$HELM_CHART_PATH/scripts/vault-provisioning.sh"
        "$HELM_CHART_PATH/scripts/vault-provisioning.sh"
    else
        log_warning "Vault provisioning script not found"
    fi
}

# Setup SealedSecrets
setup_sealed_secrets() {
    log_info "Setting up SealedSecrets..."
    
    # Check if SealedSecrets controller is installed
    if ! kubectl get deployment sealed-secrets-controller -n kube-system &> /dev/null; then
        log_info "Installing SealedSecrets controller..."
        kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml
    fi
    
    # Wait for controller to be ready
    kubectl wait --for=condition=available --timeout=300s deployment/sealed-secrets-controller -n kube-system
    
    log_success "SealedSecrets controller is ready"
}

# Setup cloud secrets
setup_cloud_secrets() {
    log_info "Setting up cloud secrets management..."
    
    if [ -f "$HELM_CHART_PATH/scripts/cloud-secrets-integration.sh" ]; then
        chmod +x "$HELM_CHART_PATH/scripts/cloud-secrets-integration.sh"
        "$HELM_CHART_PATH/scripts/cloud-secrets-integration.sh" create
    else
        log_warning "Cloud secrets integration script not found"
    fi
}

# Backup current deployment
backup_deployment() {
    if [ "$BACKUP_BEFORE_DEPLOY" = "true" ]; then
        log_info "Creating backup of current deployment..."
        
        local backup_dir="/tmp/helm-backup-$(date +%Y%m%d-%H%M%S)"
        mkdir -p "$backup_dir"
        
        # Backup current Helm release
        if helm list -n "$NAMESPACE" | grep -q "$RELEASE_NAME"; then
            helm get values "$RELEASE_NAME" -n "$NAMESPACE" > "$backup_dir/values.yaml"
            helm get manifest "$RELEASE_NAME" -n "$NAMESPACE" > "$backup_dir/manifest.yaml"
        fi
        
        # Backup Kubernetes resources
        kubectl get all -n "$NAMESPACE" -o yaml > "$backup_dir/resources.yaml"
        kubectl get secrets -n "$NAMESPACE" -o yaml > "$backup_dir/secrets.yaml"
        kubectl get configmaps -n "$NAMESPACE" -o yaml > "$backup_dir/configmaps.yaml"
        
        # Compress backup
        tar -czf "$backup_dir.tar.gz" -C "$(dirname "$backup_dir")" "$(basename "$backup_dir")"
        rm -rf "$backup_dir"
        
        log_success "Backup created: $backup_dir.tar.gz"
    fi
}

# Deploy with Helm
deploy_helm() {
    log_info "Deploying with Helm..."
    
    local helm_args=(
        "upgrade" "--install" "$RELEASE_NAME" "$HELM_CHART_PATH"
        "--namespace" "$NAMESPACE"
        "--set" "global.secretsStrategy=$SECRETS_STRATEGY"
        "--set" "global.environment=$ENVIRONMENT"
        "--wait"
        "--timeout=10m"
    )
    
    if [ "$DRY_RUN" = "true" ]; then
        helm_args+=("--dry-run" "--debug")
    fi
    
    if [ "$FORCE_UPGRADE" = "true" ]; then
        helm_args+=("--force")
    fi
    
    # Add environment-specific values
    case "$ENVIRONMENT" in
        "staging")
            helm_args+=(
                "--set" "web.replicaCount=2"
                "--set" "celery.worker.replicaCount=1"
                "--set" "celery.beat.replicaCount=1"
                "--set" "postgresql.primary.persistence.size=20Gi"
                "--set" "redis.master.persistence.size=10Gi"
                "--set" "neo4j.persistence.dataSize=30Gi"
                "--set" "kafka.persistence.size=50Gi"
                "--set" "autoscaling.minReplicas=1"
                "--set" "autoscaling.maxReplicas=5"
            )
            ;;
        "production")
            helm_args+=(
                "--set" "web.replicaCount=3"
                "--set" "celery.worker.replicaCount=2"
                "--set" "celery.beat.replicaCount=1"
                "--set" "postgresql.primary.persistence.size=100Gi"
                "--set" "redis.master.persistence.size=20Gi"
                "--set" "neo4j.persistence.dataSize=100Gi"
                "--set" "kafka.persistence.size=200Gi"
                "--set" "autoscaling.minReplicas=3"
                "--set" "autoscaling.maxReplicas=10"
                "--set" "security.mtls.enabled=true"
                "--set" "security.waf.enabled=true"
                "--set" "security.podSecurityPolicy.enabled=true"
            )
            ;;
    esac
    
    # Add secrets management specific configurations
    case "$SECRETS_STRATEGY" in
        "vault")
            helm_args+=(
                "--set" "secretsManagement.vault.enabled=true"
                "--set" "secretsManagement.sealedSecrets.enabled=false"
                "--set" "secretsManagement.cloudSecretManager.enabled=false"
            )
            ;;
        "sealed-secrets")
            helm_args+=(
                "--set" "secretsManagement.vault.enabled=false"
                "--set" "secretsManagement.sealedSecrets.enabled=true"
                "--set" "secretsManagement.cloudSecretManager.enabled=false"
            )
            ;;
        "cloud-manager")
            helm_args+=(
                "--set" "secretsManagement.vault.enabled=false"
                "--set" "secretsManagement.sealedSecrets.enabled=false"
                "--set" "secretsManagement.cloudSecretManager.enabled=true"
            )
            ;;
        "hybrid")
            helm_args+=(
                "--set" "secretsManagement.vault.enabled=true"
                "--set" "secretsManagement.sealedSecrets.enabled=true"
                "--set" "secretsManagement.cloudSecretManager.enabled=true"
            )
            ;;
    esac
    
    # Execute Helm deployment
    if helm "${helm_args[@]}"; then
        log_success "Helm deployment completed successfully"
    else
        log_error "Helm deployment failed"
        return 1
    fi
}

# Validate deployment
validate_deployment() {
    if [ "$VALIDATE_AFTER_DEPLOY" = "true" ]; then
        log_info "Validating deployment..."
        
        # Check if all pods are running
        local max_attempts=30
        local attempt=1
        
        while [ $attempt -le $max_attempts ]; do
            local running_pods=$(kubectl get pods -n "$NAMESPACE" --field-selector=status.phase=Running --no-headers | wc -l)
            local total_pods=$(kubectl get pods -n "$NAMESPACE" --no-headers | wc -l)
            
            if [ "$running_pods" -eq "$total_pods" ] && [ "$total_pods" -gt 0 ]; then
                log_success "All pods are running"
                break
            fi
            
            log_info "Waiting for pods to be ready... ($running_pods/$total_pods)"
            sleep 10
            ((attempt++))
        done
        
        if [ $attempt -gt $max_attempts ]; then
            log_error "Timeout waiting for pods to be ready"
            return 1
        fi
        
        # Check service endpoints
        local services=("cancer-genomics-web" "postgresql" "redis-master" "neo4j" "kafka")
        for service in "${services[@]}"; do
            if kubectl get service "$service" -n "$NAMESPACE" &> /dev/null; then
                local endpoint=$(kubectl get endpoints "$service" -n "$NAMESPACE" -o jsonpath='{.subsets[0].addresses[0].ip}')
                if [ -n "$endpoint" ]; then
                    log_success "Service $service has endpoint: $endpoint"
                else
                    log_warning "Service $service has no endpoints"
                fi
            fi
        done
        
        # Run health checks
        run_health_checks
        
        log_success "Deployment validation completed"
    fi
}

# Run health checks
run_health_checks() {
    log_info "Running health checks..."
    
    # Get service URL
    local service_url=$(kubectl get service cancer-genomics-web -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    if [ -z "$service_url" ]; then
        service_url=$(kubectl get service cancer-genomics-web -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    fi
    
    if [ -n "$service_url" ]; then
        # Wait for service to be ready
        sleep 30
        
        # Test health endpoint
        if curl -f "http://$service_url/health" &> /dev/null; then
            log_success "Health check passed"
        else
            log_warning "Health check failed"
        fi
        
        # Test API endpoint
        if curl -f "http://$service_url/api/health" &> /dev/null; then
            log_success "API health check passed"
        else
            log_warning "API health check failed"
        fi
    else
        log_warning "Service URL not available for health checks"
    fi
}

# Rollback deployment
rollback_deployment() {
    if [ "$ROLLBACK_ON_FAILURE" = "true" ]; then
        log_info "Rolling back deployment..."
        
        if helm rollback "$RELEASE_NAME" -n "$NAMESPACE"; then
            log_success "Rollback completed successfully"
        else
            log_error "Rollback failed"
        fi
    fi
}

# Setup monitoring
setup_monitoring() {
    log_info "Setting up monitoring..."
    
    # Deploy monitoring rules
    if [ -f "$HELM_CHART_PATH/grafana-alerting-rules.yaml" ]; then
        kubectl apply -f "$HELM_CHART_PATH/grafana-alerting-rules.yaml"
        log_success "Monitoring rules deployed"
    fi
    
    # Deploy service monitors
    kubectl apply -f "$HELM_CHART_PATH/templates/monitoring.yaml" || true
    log_success "Service monitors deployed"
}

# Setup secret rotation
setup_secret_rotation() {
    log_info "Setting up secret rotation..."
    
    if [ -f "$HELM_CHART_PATH/scripts/secret-rotation.sh" ]; then
        chmod +x "$HELM_CHART_PATH/scripts/secret-rotation.sh"
        
        # Create CronJob for secret rotation
        cat << EOF | kubectl apply -f -
apiVersion: batch/v1
kind: CronJob
metadata:
  name: secret-rotation
  namespace: $NAMESPACE
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: secret-rotation
            image: bitnami/kubectl:latest
            command:
            - /bin/bash
            - -c
            - |
              /scripts/secret-rotation.sh rotate
            volumeMounts:
            - name: scripts
              mountPath: /scripts
          volumes:
          - name: scripts
            configMap:
              name: secret-rotation-scripts
          restartPolicy: OnFailure
EOF
        
        # Create ConfigMap with scripts
        kubectl create configmap secret-rotation-scripts \
            --from-file="$HELM_CHART_PATH/scripts/secret-rotation.sh" \
            -n "$NAMESPACE" \
            --dry-run=client -o yaml | kubectl apply -f -
        
        log_success "Secret rotation setup completed"
    fi
}

# Cleanup resources
cleanup_resources() {
    log_info "Cleaning up resources..."
    
    # Remove old backups
    find /tmp -name "helm-backup-*.tar.gz" -mtime +7 -delete 2>/dev/null || true
    
    # Remove old logs
    find /tmp -name "deployment-*.log" -mtime +7 -delete 2>/dev/null || true
    
    log_success "Cleanup completed"
}

# Main deployment function
deploy() {
    log_info "Starting deployment orchestration..."
    
    # Check prerequisites
    check_prerequisites
    
    # Create namespace
    create_namespace
    
    # Setup secrets management
    setup_secrets_management
    
    # Backup current deployment
    backup_deployment
    
    # Deploy with Helm
    if deploy_helm; then
        # Validate deployment
        if validate_deployment; then
            # Setup monitoring
            setup_monitoring
            
            # Setup secret rotation
            setup_secret_rotation
            
            # Cleanup resources
            cleanup_resources
            
            log_success "Deployment orchestration completed successfully!"
        else
            log_error "Deployment validation failed"
            rollback_deployment
            exit 1
        fi
    else
        log_error "Helm deployment failed"
        rollback_deployment
        exit 1
    fi
}

# Main function
main() {
    local action="${1:-deploy}"
    shift || true
    
    case "$action" in
        "deploy")
            deploy
            ;;
        "validate")
            validate_deployment
            ;;
        "rollback")
            rollback_deployment
            ;;
        "backup")
            backup_deployment
            ;;
        "cleanup")
            cleanup_resources
            ;;
        "help"|*)
            echo "Usage: $0 {deploy|validate|rollback|backup|cleanup} [options...]"
            echo ""
            echo "Actions:"
            echo "  deploy   - Deploy the application (default)"
            echo "  validate - Validate the deployment"
            echo "  rollback - Rollback the deployment"
            echo "  backup   - Create backup of current deployment"
            echo "  cleanup  - Cleanup old resources"
            echo ""
            echo "Environment Variables:"
            echo "  HELM_CHART_PATH         - Path to Helm chart"
            echo "  RELEASE_NAME            - Helm release name"
            echo "  NAMESPACE               - Kubernetes namespace"
            echo "  ENVIRONMENT             - Environment (staging, production)"
            echo "  SECRETS_STRATEGY        - Secrets strategy (vault, sealed-secrets, cloud-manager, hybrid)"
            echo "  DRY_RUN                 - Dry run mode"
            echo "  FORCE_UPGRADE           - Force upgrade"
            echo "  BACKUP_BEFORE_DEPLOY    - Backup before deployment"
            echo "  VALIDATE_AFTER_DEPLOY   - Validate after deployment"
            echo "  ROLLBACK_ON_FAILURE     - Rollback on failure"
            echo ""
            echo "Examples:"
            echo "  $0 deploy"
            echo "  $0 validate"
            echo "  $0 rollback"
            echo "  $0 backup"
            echo "  $0 cleanup"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
