# General Variables
variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "cancer-genomics"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "dev"
  
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be one of: dev, staging, production."
  }
}

variable "gcp_project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "gcp_region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "gcp_zone" {
  description = "GCP zone"
  type        = string
  default     = "us-central1-a"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = ""
}

# GKE Variables
variable "kubernetes_version" {
  description = "Kubernetes version for GKE cluster"
  type        = string
  default     = "1.28"
}

variable "kubernetes_namespace" {
  description = "Kubernetes namespace for the application"
  type        = string
  default     = "cancer-genomics"
}

# Cloud SQL Variables
variable "cloud_sql_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-standard-2"
}

variable "cloud_sql_disk_size" {
  description = "Cloud SQL disk size in GB"
  type        = number
  default     = 100
}

# Redis Variables
variable "redis_tier" {
  description = "Memorystore Redis tier"
  type        = string
  default     = "STANDARD_HA"
  
  validation {
    condition     = contains(["BASIC", "STANDARD_HA"], var.redis_tier)
    error_message = "Redis tier must be either 'BASIC' or 'STANDARD_HA'."
  }
}

variable "redis_memory_size_gb" {
  description = "Redis memory size in GB"
  type        = number
  default     = 4
}

# Monitoring Variables
variable "log_retention_days" {
  description = "Cloud Logging retention in days"
  type        = number
  default     = 30
}

# Cost Optimization Variables
variable "enable_spot_instances" {
  description = "Enable spot instances for compute nodes"
  type        = bool
  default     = true
}

variable "enable_autoscaling" {
  description = "Enable cluster autoscaling"
  type        = bool
  default     = true
}

# Security Variables
variable "enable_encryption" {
  description = "Enable encryption for all resources"
  type        = bool
  default     = true
}

variable "enable_backup" {
  description = "Enable backup for databases"
  type        = bool
  default     = true
}

# Network Variables
variable "enable_private_cluster" {
  description = "Enable private GKE cluster"
  type        = bool
  default     = true
}

variable "enable_network_policy" {
  description = "Enable network policy"
  type        = bool
  default     = true
}

# Storage Variables
variable "enable_persistent_disks" {
  description = "Enable persistent disks"
  type        = bool
  default     = true
}

variable "disk_type" {
  description = "Disk type for nodes"
  type        = string
  default     = "pd-standard"
  
  validation {
    condition     = contains(["pd-standard", "pd-ssd", "pd-balanced"], var.disk_type)
    error_message = "Disk type must be one of: pd-standard, pd-ssd, pd-balanced."
  }
}

# Backup Variables
variable "backup_retention_days" {
  description = "Backup retention period in days"
  type        = number
  default     = 7
}

variable "backup_schedule" {
  description = "Backup schedule (cron expression)"
  type        = string
  default     = "0 2 * * *"  # Daily at 2 AM
}

# Monitoring Variables
variable "enable_cloud_monitoring" {
  description = "Enable Cloud Monitoring"
  type        = bool
  default     = true
}

variable "enable_cloud_logging" {
  description = "Enable Cloud Logging"
  type        = bool
  default     = true
}

# Alerting Variables
variable "alert_email" {
  description = "Email address for alerts"
  type        = string
  default     = ""
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for alerts"
  type        = string
  default     = ""
  sensitive   = true
}

# Performance Variables
variable "enable_workload_identity" {
  description = "Enable Workload Identity"
  type        = bool
  default     = true
}

variable "enable_binary_authorization" {
  description = "Enable Binary Authorization"
  type        = bool
  default     = true
}

# Compliance Variables
variable "enable_audit_logging" {
  description = "Enable audit logging"
  type        = bool
  default     = true
}

variable "compliance_framework" {
  description = "Compliance framework (HIPAA, SOC2, etc.)"
  type        = string
  default     = ""
  
  validation {
    condition     = var.compliance_framework == "" || contains(["HIPAA", "SOC2", "PCI", "GDPR"], var.compliance_framework)
    error_message = "Compliance framework must be one of: HIPAA, SOC2, PCI, GDPR, or empty string."
  }
}

# Disaster Recovery Variables
variable "enable_multi_az" {
  description = "Enable multi-AZ deployment"
  type        = bool
  default     = true
}

variable "enable_cross_region_backup" {
  description = "Enable cross-region backup"
  type        = bool
  default     = false
}

variable "backup_region" {
  description = "Region for cross-region backup"
  type        = string
  default     = ""
}

# Development Variables
variable "enable_debug_logging" {
  description = "Enable debug logging"
  type        = bool
  default     = false
}

variable "enable_development_tools" {
  description = "Enable development tools and debugging"
  type        = bool
  default     = false
}

# Cost Management Variables
variable "budget_limit" {
  description = "Monthly budget limit in USD"
  type        = number
  default     = 1000
}

variable "enable_cost_anomaly_detection" {
  description = "Enable cost anomaly detection"
  type        = bool
  default     = true
}

# Resource Tagging Variables
variable "additional_labels" {
  description = "Additional labels to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "owner" {
  description = "Owner of the resources"
  type        = string
  default     = "cancer-genomics-team"
}

variable "cost_center" {
  description = "Cost center for billing"
  type        = string
  default     = "research"
}

# Feature Flags
variable "enable_experimental_features" {
  description = "Enable experimental features"
  type        = bool
  default     = false
}

variable "enable_ai_ml_features" {
  description = "Enable AI/ML features"
  type        = bool
  default     = true
}

variable "enable_real_time_processing" {
  description = "Enable real-time processing"
  type        = bool
  default     = true
}

# External Dependencies
variable "external_database_host" {
  description = "External database host (if not using Cloud SQL)"
  type        = string
  default     = ""
}

variable "external_redis_host" {
  description = "External Redis host (if not using Memorystore)"
  type        = string
  default     = ""
}

# API Gateway Variables
variable "enable_api_gateway" {
  description = "Enable API Gateway"
  type        = bool
  default     = true
}

variable "api_gateway_stage" {
  description = "API Gateway stage name"
  type        = string
  default     = "v1"
}

# CDN Variables
variable "enable_cloud_cdn" {
  description = "Enable Cloud CDN"
  type        = bool
  default     = true
}

variable "cdn_cache_mode" {
  description = "CDN cache mode"
  type        = string
  default     = "CACHE_ALL_STATIC"
  
  validation {
    condition     = contains(["CACHE_ALL_STATIC", "USE_ORIGIN_HEADERS", "FORCE_CACHE_ALL", "BYPASS_CACHE"], var.cdn_cache_mode)
    error_message = "CDN cache mode must be one of: CACHE_ALL_STATIC, USE_ORIGIN_HEADERS, FORCE_CACHE_ALL, BYPASS_CACHE."
  }
}

# WAF Variables
variable "enable_cloud_armor" {
  description = "Enable Cloud Armor"
  type        = bool
  default     = true
}

variable "cloud_armor_rules" {
  description = "Cloud Armor rules to apply"
  type        = list(string)
  default     = ["owasp-crs-v030001"]
}

# Secrets Management Variables
variable "secrets_rotation_schedule" {
  description = "Schedule for secrets rotation (cron expression)"
  type        = string
  default     = "0 2 1 * *"  # Monthly on the 1st at 2 AM
}

variable "enable_secrets_rotation" {
  description = "Enable automatic secrets rotation"
  type        = bool
  default     = true
}

# Network Security Variables
variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the application"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "enable_network_firewall" {
  description = "Enable Network Firewall"
  type        = bool
  default     = false
}

# Data Classification Variables
variable "data_classification" {
  description = "Data classification level"
  type        = string
  default     = "confidential"
  
  validation {
    condition     = contains(["public", "internal", "confidential", "restricted"], var.data_classification)
    error_message = "Data classification must be one of: public, internal, confidential, restricted."
  }
}

variable "enable_data_encryption_at_rest" {
  description = "Enable encryption at rest for all data"
  type        = bool
  default     = true
}

variable "enable_data_encryption_in_transit" {
  description = "Enable encryption in transit for all data"
  type        = bool
  default     = true
}

# GKE Specific Variables
variable "enable_shielded_nodes" {
  description = "Enable Shielded GKE nodes"
  type        = bool
  default     = true
}

variable "enable_secure_boot" {
  description = "Enable Secure Boot"
  type        = bool
  default     = true
}

variable "enable_integrity_monitoring" {
  description = "Enable Integrity Monitoring"
  type        = bool
  default     = true
}

variable "enable_auto_repair" {
  description = "Enable auto-repair for node pools"
  type        = bool
  default     = true
}

variable "enable_auto_upgrade" {
  description = "Enable auto-upgrade for node pools"
  type        = bool
  default     = true
}

# Maintenance Variables
variable "maintenance_window_start_time" {
  description = "Maintenance window start time (HH:MM format)"
  type        = string
  default     = "03:00"
}

variable "maintenance_window_day" {
  description = "Maintenance window day (1-7, where 1 is Monday)"
  type        = number
  default     = 7  # Sunday
  
  validation {
    condition     = var.maintenance_window_day >= 1 && var.maintenance_window_day <= 7
    error_message = "Maintenance window day must be between 1 and 7."
  }
}

# Resource Limits
variable "max_nodes_per_pool" {
  description = "Maximum number of nodes per node pool"
  type        = number
  default     = 20
}

variable "min_nodes_per_pool" {
  description = "Minimum number of nodes per node pool"
  type        = number
  default     = 1
}

# Storage Variables
variable "enable_filestore" {
  description = "Enable Filestore for shared storage"
  type        = bool
  default     = true
}

variable "filestore_tier" {
  description = "Filestore tier"
  type        = string
  default     = "STANDARD"
  
  validation {
    condition     = contains(["STANDARD", "PREMIUM", "ENTERPRISE"], var.filestore_tier)
    error_message = "Filestore tier must be one of: STANDARD, PREMIUM, ENTERPRISE."
  }
}

variable "filestore_capacity_gb" {
  description = "Filestore capacity in GB"
  type        = number
  default     = 1024
}

# Networking Variables
variable "enable_private_google_access" {
  description = "Enable Private Google Access"
  type        = bool
  default     = true
}

variable "enable_flow_logs" {
  description = "Enable VPC Flow Logs"
  type        = bool
  default     = true
}

# Service Mesh Variables
variable "enable_istio" {
  description = "Enable Istio service mesh"
  type        = bool
  default     = false
}

variable "istio_auth" {
  description = "Istio authentication mode"
  type        = string
  default     = "AUTH_MUTUAL_TLS"
  
  validation {
    condition     = contains(["AUTH_NONE", "AUTH_MUTUAL_TLS"], var.istio_auth)
    error_message = "Istio auth must be either 'AUTH_NONE' or 'AUTH_MUTUAL_TLS'."
  }
}

# GPU Variables
variable "enable_gpu_nodes" {
  description = "Enable GPU nodes for ML workloads"
  type        = bool
  default     = false
}

variable "gpu_type" {
  description = "GPU type for ML workloads"
  type        = string
  default     = "nvidia-tesla-t4"
  
  validation {
    condition     = contains(["nvidia-tesla-t4", "nvidia-tesla-v100", "nvidia-tesla-p4", "nvidia-tesla-k80"], var.gpu_type)
    error_message = "GPU type must be one of: nvidia-tesla-t4, nvidia-tesla-v100, nvidia-tesla-p4, nvidia-tesla-k80."
  }
}

variable "gpu_count" {
  description = "Number of GPUs per node"
  type        = number
  default     = 1
}

# Cost Optimization
variable "enable_preemptible_nodes" {
  description = "Enable preemptible nodes for cost optimization"
  type        = bool
  default     = true
}

variable "enable_spot_instances" {
  description = "Enable spot instances for cost optimization"
  type        = bool
  default     = true
}

# Monitoring and Observability
variable "enable_cloud_trace" {
  description = "Enable Cloud Trace"
  type        = bool
  default     = true
}

variable "enable_cloud_profiler" {
  description = "Enable Cloud Profiler"
  type        = bool
  default     = true
}

variable "enable_error_reporting" {
  description = "Enable Error Reporting"
  type        = bool
  default     = true
}

# Security and Compliance
variable "enable_vulnerability_scanning" {
  description = "Enable vulnerability scanning"
  type        = bool
  default     = true
}

variable "enable_binary_authorization" {
  description = "Enable Binary Authorization"
  type        = bool
  default     = true
}

variable "enable_network_security_policy" {
  description = "Enable Network Security Policy"
  type        = bool
  default     = true
}
