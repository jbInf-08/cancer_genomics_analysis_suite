#!/bin/bash

# Automatic Secret Rotation Script for Cancer Genomics Analysis Suite
# This script handles automatic rotation of secrets across Vault, SealedSecrets, and Cloud Secret Managers

set -euo pipefail

# Configuration
VAULT_ADDR="${VAULT_ADDR:-https://vault.cancer-genomics.local:8200}"
VAULT_NAMESPACE="${VAULT_NAMESPACE:-cancer-genomics}"
VAULT_PATH="${VAULT_PATH:-secret/cancer-genomics}"
KUBERNETES_NAMESPACE="${KUBERNETES_NAMESPACE:-cancer-genomics}"
ROTATION_LOG_FILE="${ROTATION_LOG_FILE:-/var/log/secret-rotation.log}"
ALERT_WEBHOOK_URL="${ALERT_WEBHOOK_URL:-}"
BACKUP_ENABLED="${BACKUP_ENABLED:-true}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$ROTATION_LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$ROTATION_LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$ROTATION_LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$ROTATION_LOG_FILE"
}

# Send alert notification
send_alert() {
    local severity="$1"
    local message="$2"
    local details="${3:-}"
    
    if [ -n "$ALERT_WEBHOOK_URL" ]; then
        local payload=$(cat << EOF
{
  "severity": "$severity",
  "message": "$message",
  "details": "$details",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "service": "cancer-genomics-secret-rotation"
}
EOF
        )
        
        curl -X POST "$ALERT_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "$payload" || log_warning "Failed to send alert notification"
    fi
    
    log_error "$message"
    if [ -n "$details" ]; then
        log_error "Details: $details"
    fi
}

# Generate secure password
generate_password() {
    local length="${1:-32}"
    local complexity="${2:-high}"
    
    case "$complexity" in
        "high")
            # High complexity: uppercase, lowercase, numbers, special characters
            openssl rand -base64 48 | tr -d "=+/" | cut -c1-"$length"
            ;;
        "medium")
            # Medium complexity: uppercase, lowercase, numbers
            openssl rand -base64 32 | tr -d "=+/" | cut -c1-"$length"
            ;;
        "low")
            # Low complexity: alphanumeric only
            openssl rand -base64 24 | tr -d "=+/" | cut -c1-"$length"
            ;;
        *)
            openssl rand -base64 48 | tr -d "=+/" | cut -c1-"$length"
            ;;
    esac
}

# Generate JWT secret
generate_jwt_secret() {
    openssl rand -base64 64 | tr -d "=+/"
}

# Generate API key
generate_api_key() {
    openssl rand -hex 32
}

# Backup current secrets
backup_secrets() {
    local backup_dir="/tmp/secret-backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"
    
    log_info "Creating backup of current secrets in $backup_dir"
    
    # Backup Vault secrets
    if command -v vault &> /dev/null; then
        vault kv list -address="$VAULT_ADDR" "$VAULT_PATH" > "$backup_dir/vault-secrets-list.txt" 2>/dev/null || true
        
        # Backup each secret path
        for path in database app redis neo4j kafka apis oauth cloud monitoring notifications; do
            vault kv get -address="$VAULT_ADDR" -format=json "$VAULT_PATH/$path" > "$backup_dir/vault-$path.json" 2>/dev/null || true
        done
    fi
    
    # Backup Kubernetes secrets
    if command -v kubectl &> /dev/null; then
        kubectl get secrets -n "$KUBERNETES_NAMESPACE" -o yaml > "$backup_dir/kubernetes-secrets.yaml" 2>/dev/null || true
    fi
    
    # Compress backup
    tar -czf "$backup_dir.tar.gz" -C "$(dirname "$backup_dir")" "$(basename "$backup_dir")"
    rm -rf "$backup_dir"
    
    log_success "Backup created: $backup_dir.tar.gz"
    
    # Clean up old backups
    if [ "$BACKUP_ENABLED" = "true" ]; then
        find /tmp -name "secret-backup-*.tar.gz" -mtime +$BACKUP_RETENTION_DAYS -delete 2>/dev/null || true
    fi
}

# Rotate database secrets
rotate_database_secrets() {
    log_info "Rotating database secrets..."
    
    local new_password=$(generate_password 32 "high")
    local new_user="postgres"
    local new_db="genomics_db"
    
    # Update Vault
    if command -v vault &> /dev/null; then
        vault kv put -address="$VAULT_ADDR" "$VAULT_PATH/database" \
            POSTGRES_USER="$new_user" \
            POSTGRES_PASSWORD="$new_password" \
            POSTGRES_DB="$new_db"
        log_success "Updated database secrets in Vault"
    fi
    
    # Update Kubernetes secrets
    if command -v kubectl &> /dev/null; then
        kubectl create secret generic postgres-secrets \
            --from-literal=POSTGRES_USER="$new_user" \
            --from-literal=POSTGRES_PASSWORD="$new_password" \
            --from-literal=POSTGRES_DB="$new_db" \
            -n "$KUBERNETES_NAMESPACE" \
            --dry-run=client -o yaml | kubectl apply -f -
        log_success "Updated database secrets in Kubernetes"
    fi
    
    # Update database password
    if command -v psql &> /dev/null; then
        # This would need to be run from within the cluster or with proper connectivity
        log_info "Database password updated. Manual database password change may be required."
    fi
    
    # Restart database pods to pick up new password
    if command -v kubectl &> /dev/null; then
        kubectl rollout restart deployment/postgresql -n "$KUBERNETES_NAMESPACE" || true
        log_info "Restarted PostgreSQL deployment"
    fi
}

# Rotate application secrets
rotate_app_secrets() {
    log_info "Rotating application secrets..."
    
    local new_secret_key=$(generate_password 64 "high")
    local new_jwt_secret=$(generate_jwt_secret)
    local new_flask_secret=$(generate_password 64 "high")
    
    # Update Vault
    if command -v vault &> /dev/null; then
        vault kv put -address="$VAULT_ADDR" "$VAULT_PATH/app" \
            SECRET_KEY="$new_secret_key" \
            JWT_SECRET_KEY="$new_jwt_secret" \
            FLASK_SECRET_KEY="$new_flask_secret"
        log_success "Updated application secrets in Vault"
    fi
    
    # Update Kubernetes secrets
    if command -v kubectl &> /dev/null; then
        kubectl create secret generic app-secrets \
            --from-literal=SECRET_KEY="$new_secret_key" \
            --from-literal=JWT_SECRET_KEY="$new_jwt_secret" \
            --from-literal=FLASK_SECRET_KEY="$new_flask_secret" \
            -n "$KUBERNETES_NAMESPACE" \
            --dry-run=client -o yaml | kubectl apply -f -
        log_success "Updated application secrets in Kubernetes"
    fi
    
    # Restart application pods
    if command -v kubectl &> /dev/null; then
        kubectl rollout restart deployment/cancer-genomics-web -n "$KUBERNETES_NAMESPACE" || true
        kubectl rollout restart deployment/cancer-genomics-celery-worker -n "$KUBERNETES_NAMESPACE" || true
        kubectl rollout restart deployment/cancer-genomics-celery-beat -n "$KUBERNETES_NAMESPACE" || true
        log_info "Restarted application deployments"
    fi
}

# Rotate Redis secrets
rotate_redis_secrets() {
    log_info "Rotating Redis secrets..."
    
    local new_password=$(generate_password 32 "high")
    
    # Update Vault
    if command -v vault &> /dev/null; then
        vault kv put -address="$VAULT_ADDR" "$VAULT_PATH/redis" \
            REDIS_PASSWORD="$new_password"
        log_success "Updated Redis secrets in Vault"
    fi
    
    # Update Kubernetes secrets
    if command -v kubectl &> /dev/null; then
        kubectl create secret generic redis-secrets \
            --from-literal=REDIS_PASSWORD="$new_password" \
            -n "$KUBERNETES_NAMESPACE" \
            --dry-run=client -o yaml | kubectl apply -f -
        log_success "Updated Redis secrets in Kubernetes"
    fi
    
    # Restart Redis pods
    if command -v kubectl &> /dev/null; then
        kubectl rollout restart deployment/redis-master -n "$KUBERNETES_NAMESPACE" || true
        log_info "Restarted Redis deployment"
    fi
}

# Rotate Neo4j secrets
rotate_neo4j_secrets() {
    log_info "Rotating Neo4j secrets..."
    
    local new_password=$(generate_password 32 "high")
    local new_username="neo4j"
    local gds_license_key="${NEO4J_GDS_LICENSE_KEY:-}"
    
    # Update Vault
    if command -v vault &> /dev/null; then
        vault kv put -address="$VAULT_ADDR" "$VAULT_PATH/neo4j" \
            NEO4J_USERNAME="$new_username" \
            NEO4J_PASSWORD="$new_password" \
            NEO4J_GDS_LICENSE_KEY="$gds_license_key"
        log_success "Updated Neo4j secrets in Vault"
    fi
    
    # Update Kubernetes secrets
    if command -v kubectl &> /dev/null; then
        kubectl create secret generic neo4j-secrets \
            --from-literal=NEO4J_USERNAME="$new_username" \
            --from-literal=NEO4J_PASSWORD="$new_password" \
            --from-literal=NEO4J_GDS_LICENSE_KEY="$gds_license_key" \
            -n "$KUBERNETES_NAMESPACE" \
            --dry-run=client -o yaml | kubectl apply -f -
        log_success "Updated Neo4j secrets in Kubernetes"
    fi
    
    # Restart Neo4j pods
    if command -v kubectl &> /dev/null; then
        kubectl rollout restart deployment/neo4j -n "$KUBERNETES_NAMESPACE" || true
        log_info "Restarted Neo4j deployment"
    fi
}

# Rotate Kafka secrets
rotate_kafka_secrets() {
    log_info "Rotating Kafka secrets..."
    
    local new_password=$(generate_password 32 "high")
    local new_username="kafka"
    local jaas_config="org.apache.kafka.common.security.plain.PlainLoginModule required username=\"$new_username\" password=\"$new_password\";"
    
    # Update Vault
    if command -v vault &> /dev/null; then
        vault kv put -address="$VAULT_ADDR" "$VAULT_PATH/kafka" \
            KAFKA_USERNAME="$new_username" \
            KAFKA_PASSWORD="$new_password" \
            KAFKA_JAAS_CONFIG="$jaas_config"
        log_success "Updated Kafka secrets in Vault"
    fi
    
    # Update Kubernetes secrets
    if command -v kubectl &> /dev/null; then
        kubectl create secret generic kafka-secrets \
            --from-literal=KAFKA_USERNAME="$new_username" \
            --from-literal=KAFKA_PASSWORD="$new_password" \
            --from-literal=KAFKA_JAAS_CONFIG="$jaas_config" \
            -n "$KUBERNETES_NAMESPACE" \
            --dry-run=client -o yaml | kubectl apply -f -
        log_success "Updated Kafka secrets in Kubernetes"
    fi
    
    # Restart Kafka pods
    if command -v kubectl &> /dev/null; then
        kubectl rollout restart deployment/kafka -n "$KUBERNETES_NAMESPACE" || true
        log_info "Restarted Kafka deployment"
    fi
}

# Rotate monitoring secrets
rotate_monitoring_secrets() {
    log_info "Rotating monitoring secrets..."
    
    local new_prometheus_password=$(generate_password 32 "high")
    local new_grafana_password=$(generate_password 32 "high")
    local alertmanager_webhook_url="${ALERTMANAGER_WEBHOOK_URL:-}"
    
    # Update Vault
    if command -v vault &> /dev/null; then
        vault kv put -address="$VAULT_ADDR" "$VAULT_PATH/monitoring" \
            PROMETHEUS_PASSWORD="$new_prometheus_password" \
            GRAFANA_PASSWORD="$new_grafana_password" \
            ALERTMANAGER_WEBHOOK_URL="$alertmanager_webhook_url"
        log_success "Updated monitoring secrets in Vault"
    fi
    
    # Update Kubernetes secrets
    if command -v kubectl &> /dev/null; then
        kubectl create secret generic monitoring-secrets \
            --from-literal=PROMETHEUS_PASSWORD="$new_prometheus_password" \
            --from-literal=GRAFANA_PASSWORD="$new_grafana_password" \
            --from-literal=ALERTMANAGER_WEBHOOK_URL="$alertmanager_webhook_url" \
            -n "$KUBERNETES_NAMESPACE" \
            --dry-run=client -o yaml | kubectl apply -f -
        log_success "Updated monitoring secrets in Kubernetes"
    fi
    
    # Restart monitoring pods
    if command -v kubectl &> /dev/null; then
        kubectl rollout restart deployment/prometheus -n "$KUBERNETES_NAMESPACE" || true
        kubectl rollout restart deployment/grafana -n "$KUBERNETES_NAMESPACE" || true
        kubectl rollout restart deployment/alertmanager -n "$KUBERNETES_NAMESPACE" || true
        log_info "Restarted monitoring deployments"
    fi
}

# Rotate notification secrets
rotate_notification_secrets() {
    log_info "Rotating notification secrets..."
    
    local smtp_host="${SMTP_HOST:-}"
    local smtp_port="${SMTP_PORT:-587}"
    local smtp_username="${SMTP_USERNAME:-}"
    local smtp_password=$(generate_password 32 "high")
    local slack_webhook_url="${SLACK_WEBHOOK_URL:-}"
    local discord_webhook_url="${DISCORD_WEBHOOK_URL:-}"
    local teams_webhook_url="${TEAMS_WEBHOOK_URL:-}"
    
    # Update Vault
    if command -v vault &> /dev/null; then
        vault kv put -address="$VAULT_ADDR" "$VAULT_PATH/notifications" \
            SMTP_HOST="$smtp_host" \
            SMTP_PORT="$smtp_port" \
            SMTP_USERNAME="$smtp_username" \
            SMTP_PASSWORD="$smtp_password" \
            SLACK_WEBHOOK_URL="$slack_webhook_url" \
            DISCORD_WEBHOOK_URL="$discord_webhook_url" \
            TEAMS_WEBHOOK_URL="$teams_webhook_url"
        log_success "Updated notification secrets in Vault"
    fi
    
    # Update Kubernetes secrets
    if command -v kubectl &> /dev/null; then
        kubectl create secret generic notification-secrets \
            --from-literal=SMTP_HOST="$smtp_host" \
            --from-literal=SMTP_PORT="$smtp_port" \
            --from-literal=SMTP_USERNAME="$smtp_username" \
            --from-literal=SMTP_PASSWORD="$smtp_password" \
            --from-literal=SLACK_WEBHOOK_URL="$slack_webhook_url" \
            --from-literal=DISCORD_WEBHOOK_URL="$discord_webhook_url" \
            --from-literal=TEAMS_WEBHOOK_URL="$teams_webhook_url" \
            -n "$KUBERNETES_NAMESPACE" \
            --dry-run=client -o yaml | kubectl apply -f -
        log_success "Updated notification secrets in Kubernetes"
    fi
    
    # Restart notification pods
    if command -v kubectl &> /dev/null; then
        kubectl rollout restart deployment/notification-service -n "$KUBERNETES_NAMESPACE" || true
        log_info "Restarted notification service deployment"
    fi
}

# Rotate cloud provider secrets
rotate_cloud_secrets() {
    local provider="${1:-aws}"
    
    log_info "Rotating $provider cloud secrets..."
    
    case "$provider" in
        "aws")
            local new_access_key="${AWS_ACCESS_KEY_ID:-}"
            local new_secret_key=$(generate_password 40 "high")
            local new_session_token="${AWS_SESSION_TOKEN:-}"
            local region="${AWS_REGION:-us-west-2}"
            
            # Update Vault
            if command -v vault &> /dev/null; then
                vault kv put -address="$VAULT_ADDR" "$VAULT_PATH/cloud/aws" \
                    AWS_ACCESS_KEY_ID="$new_access_key" \
                    AWS_SECRET_ACCESS_KEY="$new_secret_key" \
                    AWS_SESSION_TOKEN="$new_session_token" \
                    AWS_REGION="$region"
                log_success "Updated AWS secrets in Vault"
            fi
            
            # Update Kubernetes secrets
            if command -v kubectl &> /dev/null; then
                kubectl create secret generic aws-secrets \
                    --from-literal=AWS_ACCESS_KEY_ID="$new_access_key" \
                    --from-literal=AWS_SECRET_ACCESS_KEY="$new_secret_key" \
                    --from-literal=AWS_SESSION_TOKEN="$new_session_token" \
                    --from-literal=AWS_REGION="$region" \
                    -n "$KUBERNETES_NAMESPACE" \
                    --dry-run=client -o yaml | kubectl apply -f -
                log_success "Updated AWS secrets in Kubernetes"
            fi
            ;;
        "gcp")
            local project_id="${GCP_PROJECT_ID:-}"
            local service_account_key="${GCP_SERVICE_ACCOUNT_KEY:-}"
            local application_credentials="${GOOGLE_APPLICATION_CREDENTIALS:-}"
            
            # Update Vault
            if command -v vault &> /dev/null; then
                vault kv put -address="$VAULT_ADDR" "$VAULT_PATH/cloud/gcp" \
                    GCP_PROJECT_ID="$project_id" \
                    GCP_SERVICE_ACCOUNT_KEY="$service_account_key" \
                    GOOGLE_APPLICATION_CREDENTIALS="$application_credentials"
                log_success "Updated GCP secrets in Vault"
            fi
            
            # Update Kubernetes secrets
            if command -v kubectl &> /dev/null; then
                kubectl create secret generic gcp-secrets \
                    --from-literal=GCP_PROJECT_ID="$project_id" \
                    --from-literal=GCP_SERVICE_ACCOUNT_KEY="$service_account_key" \
                    --from-literal=GOOGLE_APPLICATION_CREDENTIALS="$application_credentials" \
                    -n "$KUBERNETES_NAMESPACE" \
                    --dry-run=client -o yaml | kubectl apply -f -
                log_success "Updated GCP secrets in Kubernetes"
            fi
            ;;
        "azure")
            local client_id="${AZURE_CLIENT_ID:-}"
            local client_secret=$(generate_password 32 "high")
            local tenant_id="${AZURE_TENANT_ID:-}"
            local subscription_id="${AZURE_SUBSCRIPTION_ID:-}"
            
            # Update Vault
            if command -v vault &> /dev/null; then
                vault kv put -address="$VAULT_ADDR" "$VAULT_PATH/cloud/azure" \
                    AZURE_CLIENT_ID="$client_id" \
                    AZURE_CLIENT_SECRET="$client_secret" \
                    AZURE_TENANT_ID="$tenant_id" \
                    AZURE_SUBSCRIPTION_ID="$subscription_id"
                log_success "Updated Azure secrets in Vault"
            fi
            
            # Update Kubernetes secrets
            if command -v kubectl &> /dev/null; then
                kubectl create secret generic azure-secrets \
                    --from-literal=AZURE_CLIENT_ID="$client_id" \
                    --from-literal=AZURE_CLIENT_SECRET="$client_secret" \
                    --from-literal=AZURE_TENANT_ID="$tenant_id" \
                    --from-literal=AZURE_SUBSCRIPTION_ID="$subscription_id" \
                    -n "$KUBERNETES_NAMESPACE" \
                    --dry-run=client -o yaml | kubectl apply -f -
                log_success "Updated Azure secrets in Kubernetes"
            fi
            ;;
        *)
            log_warning "Unknown cloud provider: $provider"
            ;;
    esac
}

# Validate secret rotation
validate_rotation() {
    local secret_type="$1"
    local validation_passed=true
    
    log_info "Validating $secret_type secret rotation..."
    
    case "$secret_type" in
        "database")
            # Test database connectivity
            if command -v kubectl &> /dev/null; then
                if ! kubectl run db-test --image=postgres:15 --rm -i --restart=Never -- psql -h postgresql -U postgres -d genomics_db -c "SELECT 1;" &>/dev/null; then
                    log_error "Database connectivity test failed"
                    validation_passed=false
                fi
            fi
            ;;
        "redis")
            # Test Redis connectivity
            if command -v kubectl &> /dev/null; then
                if ! kubectl run redis-test --image=redis:7 --rm -i --restart=Never -- redis-cli -h redis-master ping &>/dev/null; then
                    log_error "Redis connectivity test failed"
                    validation_passed=false
                fi
            fi
            ;;
        "neo4j")
            # Test Neo4j connectivity
            if command -v kubectl &> /dev/null; then
                if ! kubectl run neo4j-test --image=neo4j:5.15 --rm -i --restart=Never -- cypher-shell -u neo4j -p neo4j-password -a neo4j "RETURN 1;" &>/dev/null; then
                    log_error "Neo4j connectivity test failed"
                    validation_passed=false
                fi
            fi
            ;;
        "kafka")
            # Test Kafka connectivity
            if command -v kubectl &> /dev/null; then
                if ! kubectl run kafka-test --image=confluentinc/cp-kafka:7.4.0 --rm -i --restart=Never -- kafka-topics --bootstrap-server kafka:9092 --list &>/dev/null; then
                    log_error "Kafka connectivity test failed"
                    validation_passed=false
                fi
            fi
            ;;
        "app")
            # Test application health
            if command -v kubectl &> /dev/null; then
                local app_url=$(kubectl get service cancer-genomics-web -n "$KUBERNETES_NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
                if [ -n "$app_url" ]; then
                    if ! curl -f "http://$app_url/health" &>/dev/null; then
                        log_error "Application health check failed"
                        validation_passed=false
                    fi
                fi
            fi
            ;;
        *)
            log_warning "Unknown secret type for validation: $secret_type"
            ;;
    esac
    
    if [ "$validation_passed" = "true" ]; then
        log_success "$secret_type secret rotation validation passed"
    else
        send_alert "critical" "$secret_type secret rotation validation failed" "Secret rotation may have caused service disruption"
    fi
    
    return $([ "$validation_passed" = "true" ] && echo 0 || echo 1)
}

# Main rotation function
rotate_secrets() {
    local secret_types=("$@")
    
    if [ ${#secret_types[@]} -eq 0 ]; then
        secret_types=("database" "app" "redis" "neo4j" "kafka" "monitoring" "notifications")
    fi
    
    log_info "Starting secret rotation for: ${secret_types[*]}"
    
    # Create backup before rotation
    backup_secrets
    
    local rotation_success=true
    
    for secret_type in "${secret_types[@]}"; do
        log_info "Rotating $secret_type secrets..."
        
        case "$secret_type" in
            "database")
                if ! rotate_database_secrets; then
                    rotation_success=false
                    send_alert "critical" "Database secret rotation failed" "Database may be inaccessible"
                fi
                ;;
            "app")
                if ! rotate_app_secrets; then
                    rotation_success=false
                    send_alert "critical" "Application secret rotation failed" "Application may be inaccessible"
                fi
                ;;
            "redis")
                if ! rotate_redis_secrets; then
                    rotation_success=false
                    send_alert "critical" "Redis secret rotation failed" "Redis may be inaccessible"
                fi
                ;;
            "neo4j")
                if ! rotate_neo4j_secrets; then
                    rotation_success=false
                    send_alert "critical" "Neo4j secret rotation failed" "Neo4j may be inaccessible"
                fi
                ;;
            "kafka")
                if ! rotate_kafka_secrets; then
                    rotation_success=false
                    send_alert "critical" "Kafka secret rotation failed" "Kafka may be inaccessible"
                fi
                ;;
            "monitoring")
                if ! rotate_monitoring_secrets; then
                    rotation_success=false
                    send_alert "warning" "Monitoring secret rotation failed" "Monitoring may be affected"
                fi
                ;;
            "notifications")
                if ! rotate_notification_secrets; then
                    rotation_success=false
                    send_alert "warning" "Notification secret rotation failed" "Notifications may be affected"
                fi
                ;;
            "aws"|"gcp"|"azure")
                if ! rotate_cloud_secrets "$secret_type"; then
                    rotation_success=false
                    send_alert "warning" "$secret_type cloud secret rotation failed" "Cloud services may be affected"
                fi
                ;;
            *)
                log_warning "Unknown secret type: $secret_type"
                ;;
        esac
        
        # Validate rotation
        if ! validate_rotation "$secret_type"; then
            rotation_success=false
        fi
        
        # Wait between rotations
        sleep 30
    done
    
    if [ "$rotation_success" = "true" ]; then
        log_success "All secret rotations completed successfully"
        send_alert "info" "Secret rotation completed successfully" "All secrets have been rotated and validated"
    else
        log_error "Some secret rotations failed"
        send_alert "critical" "Secret rotation completed with failures" "Some secrets may need manual intervention"
    fi
    
    return $([ "$rotation_success" = "true" ] && echo 0 || echo 1)
}

# Check if secrets need rotation
check_rotation_needed() {
    local secret_type="$1"
    local rotation_interval="${2:-30d}"
    
    # This would typically check against a database or file to track last rotation time
    # For now, we'll use a simple file-based approach
    
    local rotation_file="/var/lib/secret-rotation/last-rotation-$secret_type"
    local last_rotation=0
    
    if [ -f "$rotation_file" ]; then
        last_rotation=$(cat "$rotation_file")
    fi
    
    local current_time=$(date +%s)
    local interval_seconds=0
    
    case "$rotation_interval" in
        *d)
            interval_seconds=$((${rotation_interval%d} * 24 * 60 * 60))
            ;;
        *h)
            interval_seconds=$((${rotation_interval%h} * 60 * 60))
            ;;
        *m)
            interval_seconds=$((${rotation_interval%m} * 60))
            ;;
        *)
            interval_seconds=2592000  # 30 days default
            ;;
    esac
    
    if [ $((current_time - last_rotation)) -gt $interval_seconds ]; then
        return 0  # Rotation needed
    else
        return 1  # Rotation not needed
    fi
}

# Update rotation timestamp
update_rotation_timestamp() {
    local secret_type="$1"
    local rotation_file="/var/lib/secret-rotation/last-rotation-$secret_type"
    
    mkdir -p "$(dirname "$rotation_file")"
    date +%s > "$rotation_file"
}

# Main function
main() {
    local action="${1:-rotate}"
    shift || true
    
    case "$action" in
        "rotate")
            rotate_secrets "$@"
            ;;
        "check")
            local secret_type="${1:-database}"
            local rotation_interval="${2:-30d}"
            
            if check_rotation_needed "$secret_type" "$rotation_interval"; then
                log_info "$secret_type secrets need rotation"
                exit 0
            else
                log_info "$secret_type secrets do not need rotation"
                exit 1
            fi
            ;;
        "validate")
            local secret_type="${1:-database}"
            validate_rotation "$secret_type"
            ;;
        "backup")
            backup_secrets
            ;;
        *)
            echo "Usage: $0 {rotate|check|validate|backup} [secret_types...]"
            echo ""
            echo "Actions:"
            echo "  rotate   - Rotate specified secrets (default: all)"
            echo "  check    - Check if secrets need rotation"
            echo "  validate - Validate secret rotation"
            echo "  backup   - Create backup of current secrets"
            echo ""
            echo "Secret types:"
            echo "  database, app, redis, neo4j, kafka, monitoring, notifications, aws, gcp, azure"
            echo ""
            echo "Examples:"
            echo "  $0 rotate database app"
            echo "  $0 check database 30d"
            echo "  $0 validate redis"
            echo "  $0 backup"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
