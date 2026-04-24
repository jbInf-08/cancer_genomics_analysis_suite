# Vault Configuration for Cancer Genomics Analysis Suite
# This configuration provides comprehensive secrets management with automatic rotation

# Storage backend configuration
storage "consul" {
  address = "consul:8500"
  path    = "vault/"
  service = "vault"
  
  # High availability configuration
  ha_enabled = true
  redirect_addr = "https://vault.cancer-genomics.local:8200"
  cluster_addr = "https://vault.cancer-genomics.local:8201"
  
  # Performance tuning
  max_parallel = "128"
  disable_registration = false
  
  # TLS configuration
  tls_ca_file = "/vault/tls/ca.crt"
  tls_cert_file = "/vault/tls/vault.crt"
  tls_key_file = "/vault/tls/vault.key"
  tls_min_version = "tls12"
}

# Alternative storage backends (uncomment as needed)
# storage "etcd" {
#   address = "etcd:2379"
#   path = "vault/"
#   ha_enabled = true
# }

# storage "raft" {
#   path = "/vault/data"
#   node_id = "vault-node-1"
# }

# Listener configuration
listener "tcp" {
  address = "0.0.0.0:8200"
  cluster_address = "0.0.0.0:8201"
  tls_disable = false
  tls_cert_file = "/vault/tls/vault.crt"
  tls_key_file = "/vault/tls/vault.key"
  tls_min_version = "tls12"
  tls_cipher_suites = "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384,TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384"
  
  # Performance tuning
  max_request_size = 33554432
  max_request_duration = "90s"
}

# API configuration
api_addr = "https://vault.cancer-genomics.local:8200"
cluster_addr = "https://vault.cancer-genomics.local:8201"

# UI configuration
ui = true
disable_mlock = true

# Logging configuration
log_level = "INFO"
log_format = "json"
log_file = "/vault/logs/vault.log"
log_rotate_duration = "24h"
log_rotate_max_files = 30

# Telemetry configuration
telemetry {
  prometheus_retention_time = "30s"
  disable_hostname = false
  enable_hostname_label = true
  usage_gauge_period = "10m"
  maximum_gauge_cardinality = 500
}

# Seal configuration (Auto-unseal)
seal "awskms" {
  region = "us-west-2"
  kms_key_id = "alias/vault-unseal-key"
  endpoint = "https://kms.us-west-2.amazonaws.com"
}

# Alternative seal configurations
# seal "gcpckms" {
#   project = "cancer-genomics-project"
#   region = "us-west1"
#   key_ring = "vault-keyring"
#   crypto_key = "vault-unseal-key"
# }

# seal "azurekeyvault" {
#   tenant_id = "your-tenant-id"
#   vault_name = "vault-keyvault"
#   key_name = "vault-unseal-key"
# }

# Plugin directory
plugin_directory = "/vault/plugins"

# Disable caching for sensitive operations
disable_cache = false
disable_mlock = true

# Default lease TTL
default_lease_ttl = "168h"  # 7 days
max_lease_ttl = "720h"      # 30 days

# Raw storage endpoint
raw_storage_endpoint = true

# Cluster name
cluster_name = "cancer-genomics-vault"

# License (if using Vault Enterprise)
# license_path = "/vault/license/vault.hclic"

# Entropy augmentation
entropy "seal" {
  mode = "augmentation"
}

# Audit logging
audit {
  enabled = true
  path = "file"
  file_path = "/vault/logs/audit.log"
  format = "json"
  prefix = "vault_audit"
  mode = 0600
  rotate_duration = "24h"
  rotate_max_files = 30
  rotate_bytes = 100000000  # 100MB
}

# Additional audit backends
audit "syslog" {
  enabled = true
  facility = "LOCAL7"
  tag = "vault"
  format = "json"
}

# Health check configuration
# health_check_grace_period = "10s"

# Performance standby configuration
# performance_standby = true

# Replication configuration (Enterprise feature)
# replication {
#   enabled = true
#   performance_standby = true
# }

# Namespace configuration
# namespace "cancer-genomics" {
#   # Namespace-specific configuration
# }

# Service registration
service_registration "consul" {
  address = "consul:8500"
  service = "vault"
  service_tags = "vault,secrets,management"
  service_address = "vault.cancer-genomics.local"
  check_timeout = "5s"
  check_interval = "10s"
  check_path = "/v1/sys/health"
  check_tls_skip_verify = false
}

# High availability configuration
ha_storage "consul" {
  address = "consul:8500"
  path = "vault-ha/"
  service = "vault"
  redirect_addr = "https://vault.cancer-genomics.local:8200"
  cluster_addr = "https://vault.cancer-genomics.local:8201"
}

# Disaster recovery configuration
# disaster_recovery {
#   enabled = true
#   storage "s3" {
#     bucket = "vault-dr-backups"
#     region = "us-west-2"
#     path = "dr/"
#   }
# }

# Metrics configuration
metrics {
  enabled = true
  prometheus_retention_time = "30s"
  disable_hostname = false
  enable_hostname_label = true
  usage_gauge_period = "10m"
  maximum_gauge_cardinality = 500
}

# Rate limiting
# rate_limit {
#   enabled = true
#   requests_per_second = 1000
#   burst_size = 2000
# }

# CORS configuration
# cors {
#   enabled = true
#   allowed_origins = ["https://cancer-genomics.yourdomain.com"]
#   allowed_headers = ["*"]
#   allowed_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
# }

# Sentry configuration for error reporting
# sentry {
#   enabled = true
#   dsn = "https://your-sentry-dsn@sentry.io/project-id"
#   environment = "production"
# }

# Experimental features
# experimental {
#   enable_entropy_augmentation = true
# }

# Development mode (disable in production)
# development = false

# Disable clustering (single node mode)
# disable_clustering = false

# Disable performance standby
# disable_performance_standby = false

# Disable indexing
# disable_indexing = false

# Disable sentinel
# disable_sentinel = false

# Disable sentinel policy
# disable_sentinel_policy = false

# Disable sentinel policy enforcement
# disable_sentinel_policy_enforcement = false

# Disable sentinel policy enforcement for specific paths
# disable_sentinel_policy_enforcement_paths = []

# Disable sentinel policy enforcement for specific policies
# disable_sentinel_policy_enforcement_policies = []

# Disable sentinel policy enforcement for specific entities
# disable_sentinel_policy_enforcement_entities = []

# Disable sentinel policy enforcement for specific groups
# disable_sentinel_policy_enforcement_groups = []

# Disable sentinel policy enforcement for specific roles
# disable_sentinel_policy_enforcement_roles = []

# Disable sentinel policy enforcement for specific auth methods
# disable_sentinel_policy_enforcement_auth_methods = []

# Disable sentinel policy enforcement for specific secret engines
# disable_sentinel_policy_enforcement_secret_engines = []

# Disable sentinel policy enforcement for specific audit devices
# disable_sentinel_policy_enforcement_audit_devices = []

# Disable sentinel policy enforcement for specific plugins
# disable_sentinel_policy_enforcement_plugins = []

# Disable sentinel policy enforcement for specific namespaces
# disable_sentinel_policy_enforcement_namespaces = []

# Disable sentinel policy enforcement for specific mounts
# disable_sentinel_policy_enforcement_mounts = []

# Disable sentinel policy enforcement for specific paths
# disable_sentinel_policy_enforcement_paths = []

# Disable sentinel policy enforcement for specific policies
# disable_sentinel_policy_enforcement_policies = []

# Disable sentinel policy enforcement for specific entities
# disable_sentinel_policy_enforcement_entities = []

# Disable sentinel policy enforcement for specific groups
# disable_sentinel_policy_enforcement_groups = []

# Disable sentinel policy enforcement for specific roles
# disable_sentinel_policy_enforcement_roles = []

# Disable sentinel policy enforcement for specific auth methods
# disable_sentinel_policy_enforcement_auth_methods = []

# Disable sentinel policy enforcement for specific secret engines
# disable_sentinel_policy_enforcement_secret_engines = []

# Disable sentinel policy enforcement for specific audit devices
# disable_sentinel_policy_enforcement_audit_devices = []

# Disable sentinel policy enforcement for specific plugins
# disable_sentinel_policy_enforcement_plugins = []

# Disable sentinel policy enforcement for specific namespaces
# disable_sentinel_policy_enforcement_namespaces = []

# Disable sentinel policy enforcement for specific mounts
# disable_sentinel_policy_enforcement_mounts = []
