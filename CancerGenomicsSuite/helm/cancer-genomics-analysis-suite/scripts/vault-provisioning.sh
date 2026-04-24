#!/bin/bash

# Vault Provisioning Script for Cancer Genomics Analysis Suite
# This script automates Vault setup, configuration, and secret management

set -euo pipefail

# Configuration
VAULT_ADDR="${VAULT_ADDR:-https://vault.cancer-genomics.local:8200}"
VAULT_NAMESPACE="${VAULT_NAMESPACE:-cancer-genomics}"
VAULT_ROLE="${VAULT_ROLE:-cancer-genomics-role}"
VAULT_PATH="${VAULT_PATH:-secret/cancer-genomics}"
KUBERNETES_AUTH_PATH="${KUBERNETES_AUTH_PATH:-kubernetes}"
KUBERNETES_ROLE="${KUBERNETES_ROLE:-cancer-genomics-role}"
KUBERNETES_NAMESPACE="${KUBERNETES_NAMESPACE:-cancer-genomics}"
KUBERNETES_SERVICE_ACCOUNT="${KUBERNETES_SERVICE_ACCOUNT:-cancer-genomics-sa}"

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

# Check if vault CLI is installed
check_vault_cli() {
    if ! command -v vault &> /dev/null; then
        log_error "Vault CLI is not installed. Please install it first."
        exit 1
    fi
    log_success "Vault CLI is available"
}

# Check if kubectl is installed
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed. Please install it first."
        exit 1
    fi
    log_success "kubectl is available"
}

# Check Vault connectivity
check_vault_connectivity() {
    log_info "Checking Vault connectivity..."
    if vault status -address="$VAULT_ADDR" &> /dev/null; then
        log_success "Vault is accessible at $VAULT_ADDR"
    else
        log_error "Cannot connect to Vault at $VAULT_ADDR"
        exit 1
    fi
}

# Authenticate with Vault
authenticate_vault() {
    log_info "Authenticating with Vault..."
    
    # Try different authentication methods
    if [ -n "${VAULT_TOKEN:-}" ]; then
        log_info "Using VAULT_TOKEN for authentication"
        export VAULT_TOKEN
    elif [ -n "${VAULT_AUTH_METHOD:-}" ]; then
        case "$VAULT_AUTH_METHOD" in
            "kubernetes")
                authenticate_kubernetes
                ;;
            "aws")
                authenticate_aws
                ;;
            "gcp")
                authenticate_gcp
                ;;
            "azure")
                authenticate_azure
                ;;
            *)
                log_error "Unsupported authentication method: $VAULT_AUTH_METHOD"
                exit 1
                ;;
        esac
    else
        log_error "No authentication method specified. Set VAULT_TOKEN or VAULT_AUTH_METHOD"
        exit 1
    fi
}

# Kubernetes authentication
authenticate_kubernetes() {
    log_info "Authenticating with Kubernetes..."
    
    # Get the JWT token from the service account
    JWT_TOKEN=$(kubectl get secret -n "$KUBERNETES_NAMESPACE" \
        $(kubectl get serviceaccount "$KUBERNETES_SERVICE_ACCOUNT" -n "$KUBERNETES_NAMESPACE" -o jsonpath='{.secrets[0].name}') \
        -o jsonpath='{.data.token}' | base64 -d)
    
    # Authenticate with Vault
    VAULT_TOKEN=$(vault write -address="$VAULT_ADDR" \
        auth/"$KUBERNETES_AUTH_PATH"/login \
        role="$KUBERNETES_ROLE" \
        jwt="$JWT_TOKEN" \
        -format=json | jq -r '.auth.client_token')
    
    export VAULT_TOKEN
    log_success "Successfully authenticated with Kubernetes"
}

# AWS authentication
authenticate_aws() {
    log_info "Authenticating with AWS..."
    
    VAULT_TOKEN=$(vault write -address="$VAULT_ADDR" \
        auth/aws/login \
        role="${AWS_VAULT_ROLE:-cancer-genomics-aws-role}" \
        iam_http_request_method=POST \
        iam_request_url="$(aws sts get-caller-identity --query 'Arn' --output text)" \
        iam_request_body="Action=GetCallerIdentity&Version=2011-06-15" \
        iam_request_headers="$(aws sts get-caller-identity --query 'Arn' --output text)" \
        -format=json | jq -r '.auth.client_token')
    
    export VAULT_TOKEN
    log_success "Successfully authenticated with AWS"
}

# GCP authentication
authenticate_gcp() {
    log_info "Authenticating with GCP..."
    
    VAULT_TOKEN=$(vault write -address="$VAULT_ADDR" \
        auth/gcp/login \
        role="${GCP_VAULT_ROLE:-cancer-genomics-gcp-role}" \
        jwt="$(gcloud auth print-access-token)" \
        -format=json | jq -r '.auth.client_token')
    
    export VAULT_TOKEN
    log_success "Successfully authenticated with GCP"
}

# Azure authentication
authenticate_azure() {
    log_info "Authenticating with Azure..."
    
    VAULT_TOKEN=$(vault write -address="$VAULT_ADDR" \
        auth/azure/login \
        role="${AZURE_VAULT_ROLE:-cancer-genomics-azure-role}" \
        jwt="$(az account get-access-token --query accessToken -o tsv)" \
        -format=json | jq -r '.auth.client_token')
    
    export VAULT_TOKEN
    log_success "Successfully authenticated with Azure"
}

# Create namespace
create_namespace() {
    log_info "Creating Vault namespace: $VAULT_NAMESPACE"
    
    if vault namespace list -address="$VAULT_ADDR" | grep -q "$VAULT_NAMESPACE"; then
        log_warning "Namespace $VAULT_NAMESPACE already exists"
    else
        vault namespace create -address="$VAULT_ADDR" "$VAULT_NAMESPACE"
        log_success "Created namespace: $VAULT_NAMESPACE"
    fi
}

# Enable secret engines
enable_secret_engines() {
    log_info "Enabling secret engines..."
    
    # Enable KV v2 secret engine
    if vault secrets list -address="$VAULT_ADDR" | grep -q "secret/"; then
        log_warning "KV v2 secret engine already enabled"
    else
        vault secrets enable -address="$VAULT_ADDR" -path=secret kv-v2
        log_success "Enabled KV v2 secret engine"
    fi
    
    # Enable database secret engine
    if vault secrets list -address="$VAULT_ADDR" | grep -q "database/"; then
        log_warning "Database secret engine already enabled"
    else
        vault secrets enable -address="$VAULT_ADDR" -path=database database
        log_success "Enabled database secret engine"
    fi
    
    # Enable PKI secret engine
    if vault secrets list -address="$VAULT_ADDR" | grep -q "pki/"; then
        log_warning "PKI secret engine already enabled"
    else
        vault secrets enable -address="$VAULT_ADDR" -path=pki pki
        log_success "Enabled PKI secret engine"
    fi
    
    # Enable transit secret engine
    if vault secrets list -address="$VAULT_ADDR" | grep -q "transit/"; then
        log_warning "Transit secret engine already enabled"
    else
        vault secrets enable -address="$VAULT_ADDR" -path=transit transit
        log_success "Enabled transit secret engine"
    fi
}

# Configure database secret engine
configure_database_secret_engine() {
    log_info "Configuring database secret engine..."
    
    # PostgreSQL connection
    vault write -address="$VAULT_ADDR" database/config/postgresql \
        plugin_name=postgresql-database-plugin \
        connection_url="postgresql://{{username}}:{{password}}@postgresql:5432/genomics_db?sslmode=prefer" \
        allowed_roles="postgresql-role" \
        username="postgres" \
        password="postgres-password"
    
    # PostgreSQL role
    vault write -address="$VAULT_ADDR" database/roles/postgresql-role \
        db_name=postgresql \
        creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
        default_ttl="1h" \
        max_ttl="24h"
    
    log_success "Configured database secret engine"
}

# Configure PKI secret engine
configure_pki_secret_engine() {
    log_info "Configuring PKI secret engine..."
    
    # Generate root CA
    vault write -address="$VAULT_ADDR" -field=certificate pki/root/generate/internal \
        common_name="Cancer Genomics CA" \
        ttl=8760h > ca.crt
    
    # Configure CA and CRL URLs
    vault write -address="$VAULT_ADDR" pki/config/urls \
        issuing_certificates="$VAULT_ADDR/v1/pki/ca" \
        crl_distribution_points="$VAULT_ADDR/v1/pki/crl"
    
    # Create role for certificates
    vault write -address="$VAULT_ADDR" pki/roles/cancer-genomics \
        allowed_domains="cancer-genomics.local,cancer-genomics.yourdomain.com" \
        allow_subdomains=true \
        max_ttl="720h"
    
    log_success "Configured PKI secret engine"
}

# Configure transit secret engine
configure_transit_secret_engine() {
    log_info "Configuring transit secret engine..."
    
    # Create encryption key
    vault write -address="$VAULT_ADDR" -f transit/keys/cancer-genomics-key
    
    log_success "Configured transit secret engine"
}

# Enable authentication methods
enable_auth_methods() {
    log_info "Enabling authentication methods..."
    
    # Enable Kubernetes authentication
    if vault auth list -address="$VAULT_ADDR" | grep -q "kubernetes/"; then
        log_warning "Kubernetes authentication already enabled"
    else
        vault auth enable -address="$VAULT_ADDR" -path=kubernetes kubernetes
        log_success "Enabled Kubernetes authentication"
    fi
    
    # Configure Kubernetes authentication
    vault write -address="$VAULT_ADDR" auth/kubernetes/config \
        token_reviewer_jwt="$(kubectl get secret -n "$KUBERNETES_NAMESPACE" \
            $(kubectl get serviceaccount "$KUBERNETES_SERVICE_ACCOUNT" -n "$KUBERNETES_NAMESPACE" -o jsonpath='{.secrets[0].name}') \
            -o jsonpath='{.data.token}' | base64 -d)" \
        kubernetes_host="https://kubernetes.default.svc.cluster.local" \
        kubernetes_ca_cert="$(kubectl get secret -n "$KUBERNETES_NAMESPACE" \
            $(kubectl get serviceaccount "$KUBERNETES_SERVICE_ACCOUNT" -n "$KUBERNETES_NAMESPACE" -o jsonpath='{.secrets[0].name}') \
            -o jsonpath='{.data.ca\.crt}' | base64 -d)"
    
    # Create Kubernetes role
    vault write -address="$VAULT_ADDR" auth/kubernetes/role/"$KUBERNETES_ROLE" \
        bound_service_account_names="$KUBERNETES_SERVICE_ACCOUNT" \
        bound_service_account_namespaces="$KUBERNETES_NAMESPACE" \
        policies="cancer-genomics-policy" \
        ttl="1h"
    
    log_success "Configured Kubernetes authentication"
}

# Create policies
create_policies() {
    log_info "Creating Vault policies..."
    
    # Main application policy
    cat > cancer-genomics-policy.hcl << EOF
# Cancer Genomics Analysis Suite Policy
path "secret/data/cancer-genomics/*" {
  capabilities = ["read"]
}

path "secret/metadata/cancer-genomics/*" {
  capabilities = ["list", "read"]
}

path "database/creds/postgresql-role" {
  capabilities = ["read"]
}

path "pki/issue/cancer-genomics" {
  capabilities = ["create", "update"]
}

path "transit/encrypt/cancer-genomics-key" {
  capabilities = ["create", "update"]
}

path "transit/decrypt/cancer-genomics-key" {
  capabilities = ["create", "update"]
}

path "transit/rewrap/cancer-genomics-key" {
  capabilities = ["create", "update"]
}

path "transit/datakey/plaintext/cancer-genomics-key" {
  capabilities = ["create", "update"]
}

path "transit/datakey/wrapped/cancer-genomics-key" {
  capabilities = ["create", "update"]
}
EOF
    
    vault policy write -address="$VAULT_ADDR" cancer-genomics-policy cancer-genomics-policy.hcl
    log_success "Created cancer-genomics-policy"
    
    # Admin policy
    cat > cancer-genomics-admin-policy.hcl << EOF
# Cancer Genomics Analysis Suite Admin Policy
path "secret/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "database/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "pki/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "transit/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "auth/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "sys/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
EOF
    
    vault policy write -address="$VAULT_ADDR" cancer-genomics-admin-policy cancer-genomics-admin-policy.hcl
    log_success "Created cancer-genomics-admin-policy"
    
    # Clean up policy files
    rm -f cancer-genomics-policy.hcl cancer-genomics-admin-policy.hcl
}

# Create initial secrets
create_initial_secrets() {
    log_info "Creating initial secrets..."
    
    # Database secrets
    vault kv put -address="$VAULT_ADDR" "$VAULT_PATH/database" \
        POSTGRES_USER="postgres" \
        POSTGRES_PASSWORD="$(openssl rand -base64 32)" \
        POSTGRES_DB="genomics_db"
    
    # Application secrets
    vault kv put -address="$VAULT_ADDR" "$VAULT_PATH/app" \
        SECRET_KEY="$(openssl rand -base64 64)" \
        JWT_SECRET_KEY="$(openssl rand -base64 64)" \
        FLASK_SECRET_KEY="$(openssl rand -base64 64)"
    
    # Redis secrets
    vault kv put -address="$VAULT_ADDR" "$VAULT_PATH/redis" \
        REDIS_PASSWORD="$(openssl rand -base64 32)"
    
    # Neo4j secrets
    vault kv put -address="$VAULT_ADDR" "$VAULT_PATH/neo4j" \
        NEO4J_USERNAME="neo4j" \
        NEO4J_PASSWORD="$(openssl rand -base64 32)" \
        NEO4J_GDS_LICENSE_KEY=""
    
    # Kafka secrets
    vault kv put -address="$VAULT_ADDR" "$VAULT_PATH/kafka" \
        KAFKA_USERNAME="kafka" \
        KAFKA_PASSWORD="$(openssl rand -base64 32)" \
        KAFKA_JAAS_CONFIG=""
    
    # API keys (empty, to be filled manually)
    vault kv put -address="$VAULT_ADDR" "$VAULT_PATH/apis" \
        ENSEMBL_API_KEY="" \
        UNIPROT_API_KEY="" \
        CLINVAR_API_KEY="" \
        COSMIC_API_KEY="" \
        NCBI_API_KEY=""
    
    # OAuth secrets (empty, to be filled manually)
    vault kv put -address="$VAULT_ADDR" "$VAULT_PATH/oauth" \
        GOOGLE_CLIENT_ID="" \
        GOOGLE_CLIENT_SECRET="" \
        GITHUB_CLIENT_ID="" \
        GITHUB_CLIENT_SECRET="" \
        MICROSOFT_CLIENT_ID="" \
        MICROSOFT_CLIENT_SECRET=""
    
    # Cloud provider secrets (empty, to be filled manually)
    vault kv put -address="$VAULT_ADDR" "$VAULT_PATH/cloud/aws" \
        AWS_ACCESS_KEY_ID="" \
        AWS_SECRET_ACCESS_KEY="" \
        AWS_SESSION_TOKEN="" \
        AWS_REGION="us-west-2"
    
    vault kv put -address="$VAULT_ADDR" "$VAULT_PATH/cloud/gcp" \
        GCP_PROJECT_ID="" \
        GCP_SERVICE_ACCOUNT_KEY="" \
        GOOGLE_APPLICATION_CREDENTIALS=""
    
    vault kv put -address="$VAULT_ADDR" "$VAULT_PATH/cloud/azure" \
        AZURE_CLIENT_ID="" \
        AZURE_CLIENT_SECRET="" \
        AZURE_TENANT_ID="" \
        AZURE_SUBSCRIPTION_ID=""
    
    # Monitoring secrets
    vault kv put -address="$VAULT_ADDR" "$VAULT_PATH/monitoring" \
        PROMETHEUS_PASSWORD="$(openssl rand -base64 32)" \
        GRAFANA_PASSWORD="$(openssl rand -base64 32)" \
        ALERTMANAGER_WEBHOOK_URL=""
    
    # Notification secrets
    vault kv put -address="$VAULT_ADDR" "$VAULT_PATH/notifications" \
        SMTP_HOST="" \
        SMTP_PORT="587" \
        SMTP_USERNAME="" \
        SMTP_PASSWORD="" \
        SLACK_WEBHOOK_URL="" \
        DISCORD_WEBHOOK_URL="" \
        TEAMS_WEBHOOK_URL=""
    
    log_success "Created initial secrets"
}

# Setup secret rotation
setup_secret_rotation() {
    log_info "Setting up secret rotation..."
    
    # Create rotation policy
    cat > secret-rotation-policy.hcl << EOF
# Secret Rotation Policy
path "secret/data/cancer-genomics/database" {
  capabilities = ["read", "update"]
}

path "secret/data/cancer-genomics/app" {
  capabilities = ["read", "update"]
}

path "secret/data/cancer-genomics/redis" {
  capabilities = ["read", "update"]
}

path "secret/data/cancer-genomics/neo4j" {
  capabilities = ["read", "update"]
}

path "secret/data/cancer-genomics/kafka" {
  capabilities = ["read", "update"]
}

path "secret/data/cancer-genomics/monitoring" {
  capabilities = ["read", "update"]
}

path "secret/data/cancer-genomics/notifications" {
  capabilities = ["read", "update"]
}
EOF
    
    vault policy write -address="$VAULT_ADDR" secret-rotation-policy secret-rotation-policy.hcl
    log_success "Created secret rotation policy"
    
    # Create rotation token
    ROTATION_TOKEN=$(vault token create -address="$VAULT_ADDR" \
        -policy="secret-rotation-policy" \
        -ttl="8760h" \
        -format=json | jq -r '.auth.client_token')
    
    # Store rotation token as secret
    vault kv put -address="$VAULT_ADDR" "$VAULT_PATH/rotation" \
        ROTATION_TOKEN="$ROTATION_TOKEN"
    
    log_success "Created secret rotation token"
    
    # Clean up policy file
    rm -f secret-rotation-policy.hcl
}

# Create backup script
create_backup_script() {
    log_info "Creating backup script..."
    
    cat > backup-vault.sh << 'EOF'
#!/bin/bash

# Vault Backup Script
set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-https://vault.cancer-genomics.local:8200}"
BACKUP_DIR="${BACKUP_DIR:-/vault/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate backup filename
BACKUP_FILE="$BACKUP_DIR/vault-backup-$(date +%Y%m%d-%H%M%S).json"

# Create backup
vault operator raft snapshot save -address="$VAULT_ADDR" "$BACKUP_FILE"

# Compress backup
gzip "$BACKUP_FILE"

# Remove old backups
find "$BACKUP_DIR" -name "vault-backup-*.json.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $BACKUP_FILE.gz"
EOF
    
    chmod +x backup-vault.sh
    log_success "Created backup script"
}

# Create restore script
create_restore_script() {
    log_info "Creating restore script..."
    
    cat > restore-vault.sh << 'EOF'
#!/bin/bash

# Vault Restore Script
set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-https://vault.cancer-genomics.local:8200}"
BACKUP_FILE="${1:-}"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup-file>"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Decompress if needed
if [[ "$BACKUP_FILE" == *.gz ]]; then
    gunzip -c "$BACKUP_FILE" | vault operator raft snapshot restore -address="$VAULT_ADDR" -
else
    vault operator raft snapshot restore -address="$VAULT_ADDR" "$BACKUP_FILE"
fi

echo "Restore completed from: $BACKUP_FILE"
EOF
    
    chmod +x restore-vault.sh
    log_success "Created restore script"
}

# Create monitoring script
create_monitoring_script() {
    log_info "Creating monitoring script..."
    
    cat > monitor-vault.sh << 'EOF'
#!/bin/bash

# Vault Monitoring Script
set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-https://vault.cancer-genomics.local:8200}"
ALERT_WEBHOOK_URL="${ALERT_WEBHOOK_URL:-}"

# Check Vault health
HEALTH_STATUS=$(vault status -address="$VAULT_ADDR" -format=json | jq -r '.initialized')

if [ "$HEALTH_STATUS" != "true" ]; then
    echo "CRITICAL: Vault is not initialized"
    if [ -n "$ALERT_WEBHOOK_URL" ]; then
        curl -X POST "$ALERT_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d '{"text":"CRITICAL: Vault is not initialized"}'
    fi
    exit 1
fi

# Check Vault seal status
SEAL_STATUS=$(vault status -address="$VAULT_ADDR" -format=json | jq -r '.sealed')

if [ "$SEAL_STATUS" == "true" ]; then
    echo "CRITICAL: Vault is sealed"
    if [ -n "$ALERT_WEBHOOK_URL" ]; then
        curl -X POST "$ALERT_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d '{"text":"CRITICAL: Vault is sealed"}'
    fi
    exit 1
fi

# Check token expiration
TOKEN_INFO=$(vault token lookup -address="$VAULT_ADDR" -format=json)
TOKEN_TTL=$(echo "$TOKEN_INFO" | jq -r '.data.ttl')

if [ "$TOKEN_TTL" -lt 3600 ]; then
    echo "WARNING: Token expires in less than 1 hour"
    if [ -n "$ALERT_WEBHOOK_URL" ]; then
        curl -X POST "$ALERT_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d '{"text":"WARNING: Vault token expires in less than 1 hour"}'
    fi
fi

echo "Vault is healthy"
EOF
    
    chmod +x monitor-vault.sh
    log_success "Created monitoring script"
}

# Main function
main() {
    log_info "Starting Vault provisioning for Cancer Genomics Analysis Suite..."
    
    # Check prerequisites
    check_vault_cli
    check_kubectl
    
    # Authenticate with Vault
    authenticate_vault
    
    # Check connectivity
    check_vault_connectivity
    
    # Create namespace
    create_namespace
    
    # Enable secret engines
    enable_secret_engines
    
    # Configure secret engines
    configure_database_secret_engine
    configure_pki_secret_engine
    configure_transit_secret_engine
    
    # Enable authentication methods
    enable_auth_methods
    
    # Create policies
    create_policies
    
    # Create initial secrets
    create_initial_secrets
    
    # Setup secret rotation
    setup_secret_rotation
    
    # Create utility scripts
    create_backup_script
    create_restore_script
    create_monitoring_script
    
    log_success "Vault provisioning completed successfully!"
    log_info "Next steps:"
    log_info "1. Update API keys and OAuth secrets manually"
    log_info "2. Configure cloud provider secrets"
    log_info "3. Set up monitoring and alerting"
    log_info "4. Test secret injection in your applications"
    log_info "5. Schedule regular backups"
}

# Run main function
main "$@"
