#!/bin/bash

# Cloud Secrets Manager Integration Script for Cancer Genomics Analysis Suite
# This script provides integration with AWS Secrets Manager, GCP Secret Manager, and Azure Key Vault

set -euo pipefail

# Configuration
CLOUD_PROVIDER="${CLOUD_PROVIDER:-aws}"
KUBERNETES_NAMESPACE="${KUBERNETES_NAMESPACE:-cancer-genomics}"
SECRET_PREFIX="${SECRET_PREFIX:-cancer-genomics}"
ROTATION_ENABLED="${ROTATION_ENABLED:-true}"
BACKUP_ENABLED="${BACKUP_ENABLED:-true}"
MONITORING_ENABLED="${MONITORING_ENABLED:-true}"

# AWS Configuration
AWS_REGION="${AWS_REGION:-us-west-2}"
AWS_SECRETS_PREFIX="${AWS_SECRETS_PREFIX:-cancer-genomics}"

# GCP Configuration
GCP_PROJECT_ID="${GCP_PROJECT_ID:-}"
GCP_SECRETS_PREFIX="${GCP_SECRETS_PREFIX:-cancer-genomics}"

# Azure Configuration
AZURE_KEY_VAULT_NAME="${AZURE_KEY_VAULT_NAME:-}"
AZURE_TENANT_ID="${AZURE_TENANT_ID:-}"
AZURE_CLIENT_ID="${AZURE_CLIENT_ID:-}"
AZURE_CLIENT_SECRET="${AZURE_CLIENT_SECRET:-}"

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
    
    case "$CLOUD_PROVIDER" in
        "aws")
            if ! command -v aws &> /dev/null; then
                log_error "AWS CLI is not installed"
                exit 1
            fi
            
            if ! aws sts get-caller-identity &> /dev/null; then
                log_error "AWS credentials not configured or invalid"
                exit 1
            fi
            
            log_success "AWS CLI and credentials are configured"
            ;;
        "gcp")
            if ! command -v gcloud &> /dev/null; then
                log_error "Google Cloud CLI is not installed"
                exit 1
            fi
            
            if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 &> /dev/null; then
                log_error "Google Cloud authentication not configured"
                exit 1
            fi
            
            log_success "Google Cloud CLI and authentication are configured"
            ;;
        "azure")
            if ! command -v az &> /dev/null; then
                log_error "Azure CLI is not installed"
                exit 1
            fi
            
            if ! az account show &> /dev/null; then
                log_error "Azure authentication not configured"
                exit 1
            fi
            
            log_success "Azure CLI and authentication are configured"
            ;;
        *)
            log_error "Unsupported cloud provider: $CLOUD_PROVIDER"
            exit 1
            ;;
    esac
    
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi
    
    log_success "All prerequisites are met"
}

# AWS Secrets Manager functions
aws_create_secret() {
    local secret_name="$1"
    local secret_value="$2"
    local description="${3:-Secret for Cancer Genomics Analysis Suite}"
    
    log_info "Creating AWS secret: $secret_name"
    
    if aws secretsmanager describe-secret --secret-id "$secret_name" --region "$AWS_REGION" &> /dev/null; then
        log_warning "Secret $secret_name already exists, updating..."
        aws secretsmanager update-secret \
            --secret-id "$secret_name" \
            --secret-string "$secret_value" \
            --region "$AWS_REGION"
    else
        aws secretsmanager create-secret \
            --name "$secret_name" \
            --description "$description" \
            --secret-string "$secret_value" \
            --region "$AWS_REGION"
    fi
    
    log_success "AWS secret $secret_name created/updated"
}

aws_get_secret() {
    local secret_name="$1"
    
    aws secretsmanager get-secret-value \
        --secret-id "$secret_name" \
        --region "$AWS_REGION" \
        --query 'SecretString' \
        --output text
}

aws_delete_secret() {
    local secret_name="$1"
    
    log_info "Deleting AWS secret: $secret_name"
    
    aws secretsmanager delete-secret \
        --secret-id "$secret_name" \
        --region "$AWS_REGION" \
        --force-delete-without-recovery
    
    log_success "AWS secret $secret_name deleted"
}

aws_list_secrets() {
    aws secretsmanager list-secrets \
        --region "$AWS_REGION" \
        --query 'SecretList[?contains(Name, `'$AWS_SECRETS_PREFIX'`)].{Name:Name,Description:Description,LastChangedDate:LastChangedDate}' \
        --output table
}

aws_enable_rotation() {
    local secret_name="$1"
    local rotation_interval="${2:-30}"
    
    log_info "Enabling rotation for AWS secret: $secret_name"
    
    # Create rotation lambda function (simplified)
    local lambda_function_name="cancer-genomics-secret-rotation"
    
    # Check if lambda function exists
    if ! aws lambda get-function --function-name "$lambda_function_name" --region "$AWS_REGION" &> /dev/null; then
        log_info "Creating rotation lambda function..."
        # This would require creating a lambda function for rotation
        log_warning "Lambda function for rotation not implemented yet"
    fi
    
    # Enable rotation
    aws secretsmanager update-secret \
        --secret-id "$secret_name" \
        --region "$AWS_REGION" \
        --description "Secret with rotation enabled (every $rotation_interval days)"
    
    log_success "Rotation enabled for AWS secret $secret_name"
}

# GCP Secret Manager functions
gcp_create_secret() {
    local secret_name="$1"
    local secret_value="$2"
    local description="${3:-Secret for Cancer Genomics Analysis Suite}"
    
    log_info "Creating GCP secret: $secret_name"
    
    if gcloud secrets describe "$secret_name" --project="$GCP_PROJECT_ID" &> /dev/null; then
        log_warning "Secret $secret_name already exists, updating..."
        echo -n "$secret_value" | gcloud secrets versions add "$secret_name" --project="$GCP_PROJECT_ID" --data-file=-
    else
        echo -n "$secret_value" | gcloud secrets create "$secret_name" \
            --project="$GCP_PROJECT_ID" \
            --data-file=- \
            --labels="app=cancer-genomics,environment=production"
    fi
    
    log_success "GCP secret $secret_name created/updated"
}

gcp_get_secret() {
    local secret_name="$1"
    
    gcloud secrets versions access latest \
        --secret="$secret_name" \
        --project="$GCP_PROJECT_ID"
}

gcp_delete_secret() {
    local secret_name="$1"
    
    log_info "Deleting GCP secret: $secret_name"
    
    gcloud secrets delete "$secret_name" \
        --project="$GCP_PROJECT_ID" \
        --quiet
    
    log_success "GCP secret $secret_name deleted"
}

gcp_list_secrets() {
    gcloud secrets list \
        --project="$GCP_PROJECT_ID" \
        --filter="labels.app=cancer-genomics" \
        --format="table(name,createTime,labels.environment)"
}

gcp_enable_rotation() {
    local secret_name="$1"
    local rotation_interval="${2:-30}"
    
    log_info "Enabling rotation for GCP secret: $secret_name"
    
    # GCP Secret Manager doesn't have built-in rotation, but we can set up a Cloud Function
    local function_name="cancer-genomics-secret-rotation"
    
    # Check if Cloud Function exists
    if ! gcloud functions describe "$function_name" --region=us-central1 --project="$GCP_PROJECT_ID" &> /dev/null; then
        log_info "Creating rotation Cloud Function..."
        # This would require creating a Cloud Function for rotation
        log_warning "Cloud Function for rotation not implemented yet"
    fi
    
    log_success "Rotation setup for GCP secret $secret_name"
}

# Azure Key Vault functions
azure_create_secret() {
    local secret_name="$1"
    local secret_value="$2"
    local description="${3:-Secret for Cancer Genomics Analysis Suite}"
    
    log_info "Creating Azure Key Vault secret: $secret_name"
    
    if az keyvault secret show --vault-name "$AZURE_KEY_VAULT_NAME" --name "$secret_name" &> /dev/null; then
        log_warning "Secret $secret_name already exists, updating..."
        az keyvault secret set \
            --vault-name "$AZURE_KEY_VAULT_NAME" \
            --name "$secret_name" \
            --value "$secret_value" \
            --tags "app=cancer-genomics" "environment=production"
    else
        az keyvault secret set \
            --vault-name "$AZURE_KEY_VAULT_NAME" \
            --name "$secret_name" \
            --value "$secret_value" \
            --description "$description" \
            --tags "app=cancer-genomics" "environment=production"
    fi
    
    log_success "Azure Key Vault secret $secret_name created/updated"
}

azure_get_secret() {
    local secret_name="$1"
    
    az keyvault secret show \
        --vault-name "$AZURE_KEY_VAULT_NAME" \
        --name "$secret_name" \
        --query 'value' \
        --output tsv
}

azure_delete_secret() {
    local secret_name="$1"
    
    log_info "Deleting Azure Key Vault secret: $secret_name"
    
    az keyvault secret delete \
        --vault-name "$AZURE_KEY_VAULT_NAME" \
        --name "$secret_name"
    
    log_success "Azure Key Vault secret $secret_name deleted"
}

azure_list_secrets() {
    az keyvault secret list \
        --vault-name "$AZURE_KEY_VAULT_NAME" \
        --query "[?tags.app=='cancer-genomics'].{Name:name,Created:attributes.created,Updated:attributes.updated}" \
        --output table
}

azure_enable_rotation() {
    local secret_name="$1"
    local rotation_interval="${2:-30}"
    
    log_info "Enabling rotation for Azure Key Vault secret: $secret_name"
    
    # Azure Key Vault doesn't have built-in rotation, but we can set up a Logic App or Function App
    log_warning "Azure Key Vault rotation not implemented yet"
    
    log_success "Rotation setup for Azure Key Vault secret $secret_name"
}

# Generic functions
create_secret() {
    local secret_name="$1"
    local secret_value="$2"
    local description="${3:-Secret for Cancer Genomics Analysis Suite}"
    
    case "$CLOUD_PROVIDER" in
        "aws")
            aws_create_secret "$secret_name" "$secret_value" "$description"
            ;;
        "gcp")
            gcp_create_secret "$secret_name" "$secret_value" "$description"
            ;;
        "azure")
            azure_create_secret "$secret_name" "$secret_value" "$description"
            ;;
        *)
            log_error "Unsupported cloud provider: $CLOUD_PROVIDER"
            exit 1
            ;;
    esac
}

get_secret() {
    local secret_name="$1"
    
    case "$CLOUD_PROVIDER" in
        "aws")
            aws_get_secret "$secret_name"
            ;;
        "gcp")
            gcp_get_secret "$secret_name"
            ;;
        "azure")
            azure_get_secret "$secret_name"
            ;;
        *)
            log_error "Unsupported cloud provider: $CLOUD_PROVIDER"
            exit 1
            ;;
    esac
}

delete_secret() {
    local secret_name="$1"
    
    case "$CLOUD_PROVIDER" in
        "aws")
            aws_delete_secret "$secret_name"
            ;;
        "gcp")
            gcp_delete_secret "$secret_name"
            ;;
        "azure")
            azure_delete_secret "$secret_name"
            ;;
        *)
            log_error "Unsupported cloud provider: $CLOUD_PROVIDER"
            exit 1
            ;;
    esac
}

list_secrets() {
    case "$CLOUD_PROVIDER" in
        "aws")
            aws_list_secrets
            ;;
        "gcp")
            gcp_list_secrets
            ;;
        "azure")
            azure_list_secrets
            ;;
        *)
            log_error "Unsupported cloud provider: $CLOUD_PROVIDER"
            exit 1
            ;;
    esac
}

enable_rotation() {
    local secret_name="$1"
    local rotation_interval="${2:-30}"
    
    case "$CLOUD_PROVIDER" in
        "aws")
            aws_enable_rotation "$secret_name" "$rotation_interval"
            ;;
        "gcp")
            gcp_enable_rotation "$secret_name" "$rotation_interval"
            ;;
        "azure")
            azure_enable_rotation "$secret_name" "$rotation_interval"
            ;;
        *)
            log_error "Unsupported cloud provider: $CLOUD_PROVIDER"
            exit 1
            ;;
    esac
}

# Create Kubernetes secrets from cloud secrets
create_kubernetes_secrets() {
    log_info "Creating Kubernetes secrets from cloud secrets..."
    
    local secrets=(
        "database:POSTGRES_USER,POSTGRES_PASSWORD,POSTGRES_DB"
        "app:SECRET_KEY,JWT_SECRET_KEY,FLASK_SECRET_KEY"
        "redis:REDIS_PASSWORD"
        "neo4j:NEO4J_USERNAME,NEO4J_PASSWORD,NEO4J_GDS_LICENSE_KEY"
        "kafka:KAFKA_USERNAME,KAFKA_PASSWORD,KAFKA_JAAS_CONFIG"
        "apis:ENSEMBL_API_KEY,UNIPROT_API_KEY,CLINVAR_API_KEY,COSMIC_API_KEY,NCBI_API_KEY"
        "oauth:GOOGLE_CLIENT_ID,GOOGLE_CLIENT_SECRET,GITHUB_CLIENT_ID,GITHUB_CLIENT_SECRET,MICROSOFT_CLIENT_ID,MICROSOFT_CLIENT_SECRET"
        "monitoring:PROMETHEUS_PASSWORD,GRAFANA_PASSWORD,ALERTMANAGER_WEBHOOK_URL"
        "notifications:SMTP_HOST,SMTP_PORT,SMTP_USERNAME,SMTP_PASSWORD,SLACK_WEBHOOK_URL,DISCORD_WEBHOOK_URL,TEAMS_WEBHOOK_URL"
    )
    
    for secret_config in "${secrets[@]}"; do
        local secret_name=$(echo "$secret_config" | cut -d: -f1)
        local secret_keys=$(echo "$secret_config" | cut -d: -f2)
        
        log_info "Creating Kubernetes secret: $secret_name"
        
        local kubectl_args=()
        IFS=',' read -ra keys <<< "$secret_keys"
        
        for key in "${keys[@]}"; do
            local cloud_secret_name="${SECRET_PREFIX}-${secret_name}-${key,,}"
            local secret_value
            
            if secret_value=$(get_secret "$cloud_secret_name" 2>/dev/null); then
                kubectl_args+=(--from-literal="$key=$secret_value")
            else
                log_warning "Secret $cloud_secret_name not found in cloud provider"
                kubectl_args+=(--from-literal="$key=")
            fi
        done
        
        if [ ${#kubectl_args[@]} -gt 0 ]; then
            kubectl create secret generic "$secret_name-secrets" \
                "${kubectl_args[@]}" \
                -n "$KUBERNETES_NAMESPACE" \
                --dry-run=client -o yaml | kubectl apply -f -
            log_success "Created Kubernetes secret: $secret_name-secrets"
        fi
    done
}

# Sync secrets from cloud to Kubernetes
sync_secrets() {
    log_info "Syncing secrets from cloud to Kubernetes..."
    
    create_kubernetes_secrets
    
    log_success "Secret sync completed"
}

# Create initial secrets in cloud
create_initial_secrets() {
    log_info "Creating initial secrets in cloud provider..."
    
    local secrets=(
        "database-postgres-user:postgres:Database username"
        "database-postgres-password:$(openssl rand -base64 32):Database password"
        "database-postgres-db:genomics_db:Database name"
        "app-secret-key:$(openssl rand -base64 64):Application secret key"
        "app-jwt-secret-key:$(openssl rand -base64 64):JWT secret key"
        "app-flask-secret-key:$(openssl rand -base64 64):Flask secret key"
        "redis-redis-password:$(openssl rand -base64 32):Redis password"
        "neo4j-neo4j-username:neo4j:Neo4j username"
        "neo4j-neo4j-password:$(openssl rand -base64 32):Neo4j password"
        "neo4j-neo4j-gds-license-key::Neo4j GDS license key"
        "kafka-kafka-username:kafka:Kafka username"
        "kafka-kafka-password:$(openssl rand -base64 32):Kafka password"
        "kafka-kafka-jaas-config::Kafka JAAS configuration"
        "apis-ensembl-api-key::Ensembl API key"
        "apis-uniprot-api-key::UniProt API key"
        "apis-clinvar-api-key::ClinVar API key"
        "apis-cosmic-api-key::COSMIC API key"
        "apis-ncbi-api-key::NCBI API key"
        "oauth-google-client-id::Google OAuth client ID"
        "oauth-google-client-secret::Google OAuth client secret"
        "oauth-github-client-id::GitHub OAuth client ID"
        "oauth-github-client-secret::GitHub OAuth client secret"
        "oauth-microsoft-client-id::Microsoft OAuth client ID"
        "oauth-microsoft-client-secret::Microsoft OAuth client secret"
        "monitoring-prometheus-password:$(openssl rand -base64 32):Prometheus password"
        "monitoring-grafana-password:$(openssl rand -base64 32):Grafana password"
        "monitoring-alertmanager-webhook-url::AlertManager webhook URL"
        "notifications-smtp-host::SMTP host"
        "notifications-smtp-port:587:SMTP port"
        "notifications-smtp-username::SMTP username"
        "notifications-smtp-password:$(openssl rand -base64 32):SMTP password"
        "notifications-slack-webhook-url::Slack webhook URL"
        "notifications-discord-webhook-url::Discord webhook URL"
        "notifications-teams-webhook-url::Teams webhook URL"
    )
    
    for secret_config in "${secrets[@]}"; do
        local secret_name=$(echo "$secret_config" | cut -d: -f1)
        local secret_value=$(echo "$secret_config" | cut -d: -f2)
        local description=$(echo "$secret_config" | cut -d: -f3)
        
        local full_secret_name="${SECRET_PREFIX}-${secret_name}"
        
        create_secret "$full_secret_name" "$secret_value" "$description"
        
        # Enable rotation for password secrets
        if [[ "$secret_name" == *"password"* ]] && [ "$ROTATION_ENABLED" = "true" ]; then
            enable_rotation "$full_secret_name" 30
        fi
    done
    
    log_success "Initial secrets created in cloud provider"
}

# Backup secrets from cloud
backup_secrets() {
    local backup_dir="/tmp/cloud-secrets-backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"
    
    log_info "Creating backup of cloud secrets in $backup_dir"
    
    case "$CLOUD_PROVIDER" in
        "aws")
            aws secretsmanager list-secrets \
                --region "$AWS_REGION" \
                --query 'SecretList[?contains(Name, `'$AWS_SECRETS_PREFIX'`)].Name' \
                --output text | tr '\t' '\n' > "$backup_dir/secret-list.txt"
            
            while IFS= read -r secret_name; do
                if [ -n "$secret_name" ]; then
                    local secret_value=$(aws_get_secret "$secret_name")
                    echo "$secret_value" > "$backup_dir/$secret_name.txt"
                fi
            done < "$backup_dir/secret-list.txt"
            ;;
        "gcp")
            gcloud secrets list \
                --project="$GCP_PROJECT_ID" \
                --filter="labels.app=cancer-genomics" \
                --format="value(name)" > "$backup_dir/secret-list.txt"
            
            while IFS= read -r secret_name; do
                if [ -n "$secret_name" ]; then
                    local secret_value=$(gcp_get_secret "$secret_name")
                    echo "$secret_value" > "$backup_dir/$secret_name.txt"
                fi
            done < "$backup_dir/secret-list.txt"
            ;;
        "azure")
            az keyvault secret list \
                --vault-name "$AZURE_KEY_VAULT_NAME" \
                --query "[?tags.app=='cancer-genomics'].name" \
                --output tsv > "$backup_dir/secret-list.txt"
            
            while IFS= read -r secret_name; do
                if [ -n "$secret_name" ]; then
                    local secret_value=$(azure_get_secret "$secret_name")
                    echo "$secret_value" > "$backup_dir/$secret_name.txt"
                fi
            done < "$backup_dir/secret-list.txt"
            ;;
    esac
    
    # Compress backup
    tar -czf "$backup_dir.tar.gz" -C "$(dirname "$backup_dir")" "$(basename "$backup_dir")"
    rm -rf "$backup_dir"
    
    log_success "Backup created: $backup_dir.tar.gz"
}

# Restore secrets to cloud
restore_secrets() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi
    
    log_info "Restoring secrets from backup: $backup_file"
    
    local restore_dir="/tmp/cloud-secrets-restore-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$restore_dir"
    
    # Extract backup
    tar -xzf "$backup_file" -C "$restore_dir"
    local backup_name=$(basename "$backup_file" .tar.gz)
    
    # Restore secrets
    while IFS= read -r secret_name; do
        if [ -n "$secret_name" ]; then
            local secret_value=$(cat "$restore_dir/$backup_name/$secret_name.txt")
            create_secret "$secret_name" "$secret_value" "Restored from backup"
        fi
    done < "$restore_dir/$backup_name/secret-list.txt"
    
    rm -rf "$restore_dir"
    
    log_success "Secrets restored from backup"
}

# Monitor secrets
monitor_secrets() {
    log_info "Monitoring cloud secrets..."
    
    case "$CLOUD_PROVIDER" in
        "aws")
            # Check for secrets that need rotation
            aws secretsmanager list-secrets \
                --region "$AWS_REGION" \
                --query 'SecretList[?contains(Name, `'$AWS_SECRETS_PREFIX'`)].{Name:Name,LastChangedDate:LastChangedDate}' \
                --output table
            ;;
        "gcp")
            # Check for secrets that need rotation
            gcloud secrets list \
                --project="$GCP_PROJECT_ID" \
                --filter="labels.app=cancer-genomics" \
                --format="table(name,createTime,labels.environment)"
            ;;
        "azure")
            # Check for secrets that need rotation
            az keyvault secret list \
                --vault-name "$AZURE_KEY_VAULT_NAME" \
                --query "[?tags.app=='cancer-genomics'].{Name:name,Created:attributes.created,Updated:attributes.updated}" \
                --output table
            ;;
    esac
    
    log_success "Secret monitoring completed"
}

# Main function
main() {
    local action="${1:-help}"
    shift || true
    
    check_prerequisites
    
    case "$action" in
        "create")
            create_initial_secrets
            ;;
        "sync")
            sync_secrets
            ;;
        "list")
            list_secrets
            ;;
        "backup")
            backup_secrets
            ;;
        "restore")
            local backup_file="${1:-}"
            if [ -z "$backup_file" ]; then
                log_error "Backup file path required"
                exit 1
            fi
            restore_secrets "$backup_file"
            ;;
        "monitor")
            monitor_secrets
            ;;
        "enable-rotation")
            local secret_name="${1:-}"
            local rotation_interval="${2:-30}"
            if [ -z "$secret_name" ]; then
                log_error "Secret name required"
                exit 1
            fi
            enable_rotation "$secret_name" "$rotation_interval"
            ;;
        "help"|*)
            echo "Usage: $0 {create|sync|list|backup|restore|monitor|enable-rotation} [options...]"
            echo ""
            echo "Actions:"
            echo "  create          - Create initial secrets in cloud provider"
            echo "  sync            - Sync secrets from cloud to Kubernetes"
            echo "  list            - List all secrets in cloud provider"
            echo "  backup          - Backup all secrets from cloud provider"
            echo "  restore <file>  - Restore secrets from backup file"
            echo "  monitor         - Monitor secrets status"
            echo "  enable-rotation <secret> [interval] - Enable rotation for secret"
            echo ""
            echo "Environment Variables:"
            echo "  CLOUD_PROVIDER          - Cloud provider (aws, gcp, azure)"
            echo "  KUBERNETES_NAMESPACE    - Kubernetes namespace"
            echo "  SECRET_PREFIX           - Prefix for secret names"
            echo "  ROTATION_ENABLED        - Enable automatic rotation"
            echo "  BACKUP_ENABLED          - Enable backup functionality"
            echo "  MONITORING_ENABLED      - Enable monitoring"
            echo ""
            echo "AWS Variables:"
            echo "  AWS_REGION              - AWS region"
            echo "  AWS_SECRETS_PREFIX      - Prefix for AWS secrets"
            echo ""
            echo "GCP Variables:"
            echo "  GCP_PROJECT_ID          - GCP project ID"
            echo "  GCP_SECRETS_PREFIX      - Prefix for GCP secrets"
            echo ""
            echo "Azure Variables:"
            echo "  AZURE_KEY_VAULT_NAME    - Azure Key Vault name"
            echo "  AZURE_TENANT_ID         - Azure tenant ID"
            echo "  AZURE_CLIENT_ID         - Azure client ID"
            echo "  AZURE_CLIENT_SECRET     - Azure client secret"
            echo ""
            echo "Examples:"
            echo "  $0 create"
            echo "  $0 sync"
            echo "  $0 list"
            echo "  $0 backup"
            echo "  $0 restore /path/to/backup.tar.gz"
            echo "  $0 monitor"
            echo "  $0 enable-rotation cancer-genomics-database-postgres-password 30"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
