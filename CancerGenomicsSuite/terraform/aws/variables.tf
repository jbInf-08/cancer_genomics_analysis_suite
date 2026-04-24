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

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = ""
}

# EKS Variables
variable "kubernetes_version" {
  description = "Kubernetes version for EKS cluster"
  type        = string
  default     = "1.28"
}

variable "kubernetes_namespace" {
  description = "Kubernetes namespace for the application"
  type        = string
  default     = "cancer-genomics"
}

variable "eks_admin_users" {
  description = "List of IAM users that can access the EKS cluster"
  type        = list(object({
    userarn  = string
    username = string
    groups   = list(string)
  }))
  default = []
}

# RDS Variables
variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "rds_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 100
}

# Redis Variables
variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.medium"
}

variable "redis_num_cache_nodes" {
  description = "Number of cache nodes in Redis cluster"
  type        = number
  default     = 2
}

# Monitoring Variables
variable "log_retention_days" {
  description = "CloudWatch log retention in days"
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
variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnets"
  type        = bool
  default     = true
}

variable "enable_vpn_gateway" {
  description = "Enable VPN Gateway"
  type        = bool
  default     = false
}

# Storage Variables
variable "enable_efs" {
  description = "Enable EFS for shared storage"
  type        = bool
  default     = true
}

variable "efs_throughput_mode" {
  description = "EFS throughput mode (provisioned or bursting)"
  type        = string
  default     = "bursting"
  
  validation {
    condition     = contains(["provisioned", "bursting"], var.efs_throughput_mode)
    error_message = "EFS throughput mode must be either 'provisioned' or 'bursting'."
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
variable "enable_cloudwatch_insights" {
  description = "Enable CloudWatch Container Insights"
  type        = bool
  default     = true
}

variable "enable_xray_tracing" {
  description = "Enable X-Ray tracing"
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
variable "enable_enhanced_monitoring" {
  description = "Enable enhanced monitoring for RDS"
  type        = bool
  default     = true
}

variable "enable_performance_insights" {
  description = "Enable Performance Insights for RDS"
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
variable "additional_tags" {
  description = "Additional tags to apply to all resources"
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
  description = "External database host (if not using RDS)"
  type        = string
  default     = ""
}

variable "external_redis_host" {
  description = "External Redis host (if not using ElastiCache)"
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
variable "enable_cloudfront" {
  description = "Enable CloudFront CDN"
  type        = bool
  default     = true
}

variable "cloudfront_price_class" {
  description = "CloudFront price class"
  type        = string
  default     = "PriceClass_100"
  
  validation {
    condition     = contains(["PriceClass_All", "PriceClass_200", "PriceClass_100"], var.cloudfront_price_class)
    error_message = "CloudFront price class must be one of: PriceClass_All, PriceClass_200, PriceClass_100."
  }
}

# WAF Variables
variable "enable_waf" {
  description = "Enable AWS WAF"
  type        = bool
  default     = true
}

variable "waf_rules" {
  description = "WAF rules to apply"
  type        = list(string)
  default     = ["AWSManagedRulesCommonRuleSet", "AWSManagedRulesKnownBadInputsRuleSet"]
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
  description = "Enable AWS Network Firewall"
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
